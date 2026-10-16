# Rakathon 2026 — kdo nedorazí na mamografický screening (VZP)

Предсказываем риск того, что адресно приглашённая клиентка **не пройдёт** маммографический
скрининг в течение 12 месяцев после приглашения; объясняем факторы, сегментируем, предлагаем
интервенции и считаем размер A/B-теста.

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

python -m screening synth                              # Synthetic data -> data/raw/synthetic.parquet
python -m screening profile                            # Data overview and leakage check
python -m screening train --time-budget 60 --n-trials 20
python -m screening score --input data/raw/new.csv     # Risk + segment + intervention -> reports/scored.csv
mlflow ui --backend-store-uri sqlite:///mlflow.db      # http://127.0.0.1:5000
python -m screening power --p 0.10 --mde 0.02          # Sample size per A/B arm

pytest -m "not slow"     # Fast tests; `pytest` also runs the end-to-end test
```

## Когда придут реальные данные

1. Положить файл в `data/raw/` (папка в `.gitignore`, **данные не коммитим**).
2. В [configs/config.yaml](configs/config.yaml): `data.path`, маппинг `columns`
   (`реальное_имя: каноническое_имя`, канонические — в [schema.py](src/screening/data/schema.py)),
   `data.cutoff_date` = дата выгрузки, `split.test_year`.
3. `python -m screening profile` — пропуски, явка по годам/приглашениям, дубликаты и
   **детектор утечек** (признак с AUC > `features.leakage_auc_warn` в одиночку). Все признаки
   должны быть **на дату приглашения**; подозрительное — в `features.exclude`.
4. Обязательные колонки: `client_id`, `invitation_date`, `attended_12m` (0/1 или ANO/NE).
   Остальные опциональны — фичи и сегменты строятся только из того, что есть.
5. Для 1,3 млн строк: `optuna.tune_sample_clients: 100000` — тюнинг и выбор чемпиона на
   подвыборке клиенток, финальное обучение на всём train.

## Пайплайн

```
load ─► features ─► out-of-time split (train < test_year, test = test_year)
                     │
                     ├─► FLAML AutoML (GroupKFold по client_id) — выбор семейства моделей
                     │        └─ лучший конфиг LightGBM ─► warm-start для Optuna
                     ├─► Optuna: тюнинг LightGBM, early stopping, MedianPruner
                     ├─► чемпион: FLAML-лучшая vs Optuna-LightGBM на одних и тех же фолдах
                     └─► финальная модель ─► тест vs правило-baseline
                                               ├─ decile / calibration tables
                                               ├─ SHAP (LightGBM) / permutation (иначе)
                                               ├─ сегменты + интервенции
                                               └─ размер A/B по сегментам
```

Всё логируется в MLflow: родительский run `train`, вложенные — `flaml` и каждый
`optuna_trial_N`. CSV-отчёты дублируются в `reports/`, модель — в `models/model.joblib`
(бандл: модель + список признаков + уровни категорий; его читает `score`).

Таргет модели — `non_attendance = 1 − attended_12m` (положительный класс — неявка, ~81 %).

## Структура

| Модуль | Блок задания | Что делает |
|---|---|---|
| `data/load.py`, `data/split.py` | — | загрузка, маппинг колонок, обрезка незакрытого окна, temporal split + GroupKFold |
| `data/synthetic.py` | — | синтетика, откалиброванная под слайд 4 (≈19 % / 45 % / ≈3 %) |
| `features/build.py` | 01 KDO | производные признаки (только из имеющихся колонок) |
| `models/baseline.py` | 01 KDO | правило «число прошлых приглашений» — модель должна его побить |
| `data/profile.py` | — | обзор данных, single-feature AUC для поиска утечек |
| `models/flaml_search.py`, `models/optuna_tune.py` | 01 KDO | FLAML → Optuna |
| `models/champion.py` | 01 KDO | выбор финальной модели по CV на одинаковых фолдах (тест не используется) |
| `scoring.py` | 03 CO | скоринг новых приглашений: риск, дециль, сегмент, интервенция |
| `evaluation/metrics.py` | 01 KDO | AUC, PR-AUC, Brier, precision/lift@top-k, децили, калибровка |
| `evaluation/explain.py` | 02 PROČ | SHAP (LightGBM) или permutation-важности + направление влияния |
| `segments/rules.py` | 02–03 | сегменты-гипотезы со слайда 8 + интервенции |
| `experiment/power.py` | 04 JAK OVĚŘIT | размер выборки для A/B (две пропорции, ITT) |

## Важные оговорки

- **Высокий риск ≠ высокий эффект интервенции.** Модель ранжирует риск; кому интервенция
  *помогает*, покажет только эксперимент (дальше — uplift-модель на его результатах).
- SHAP показывает ассоциации, не причины.
- Одна клиентка встречается в нескольких годах — случайный split завышает метрики.
