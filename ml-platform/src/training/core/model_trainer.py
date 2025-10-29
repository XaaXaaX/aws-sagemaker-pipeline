from logging import Logger
import numpy as np
from kink import inject
import fireducks.pandas as pd
from pandas import DataFrame
from sklearn.model_selection import ParameterGrid
from catboost import CatBoostRanker, Pool
from fs_repository_interface import FileSystemRepository

@inject()
class ModelTrainer:
    MAX_COUNT = 50000
    TARGET_LABEL = "relevance"
    PREDICTION_LABEL = "pred_score"
    GROUPINGS = ["category"]
    FULL_FEATURES = [ 
        "category", 
        "price", 
        "price_rel_cat", 
        "views_norm", 
        "price_x_views",
        "price_rel_cat_x_views",
    ]
    STUDENT_FEATURES=[ "category", "price" ]

    def __init__(self, repository: FileSystemRepository, logger: Logger) -> None:
        self.repository = repository
        self.logger = logger

    def categorize_columns(self, df, category_features):
        for col in category_features:
            df[col] = df[col].astype("category").astype(str)

        return df

    def get_stds(self, df, features, target, grouping):
        X = df[features]
        X_std = X.iloc[:self.MAX_COUNT].copy()
        X_std = X_std.sort_values(by=grouping)
        y_std = df[target].iloc[:self.MAX_COUNT].fillna(0)
        group_ids = X_std[grouping]
        return X_std, y_std, group_ids

    def train_with_params(self, train_pool, test_pool, params, model_type):
        self.logger.debug(f"[Training]: Hyper Params: \n {params}")

        model_prefix = f"{params['loss_function']}-{params['depth']}-{params['l2_leaf_reg']}-{params['learning_rate']}-{model_type}"
        self.logger.info(f"[Training]: Model Prefix: {model_prefix}")
        ranking_model = CatBoostRanker(
                **params,
                verbose=500,
                # metric_period=50,
                eval_metric="NDCG:top=5;hints=skip_train~false",
            )

        ranking_model.fit(
                train_pool,
                eval_set=test_pool,
            )

        return model_prefix, ranking_model

    def evaluate_model(self, df, ranking_model, categorical_columns, features, target, model_name):
        binary_target = f"{target}_binary"
        threshold = np.percentile(df[target], 30)
        df[binary_target] = (df[target] >= threshold).astype(int)

        X_test_std, y_test_std, group_ids_test = self.get_stds(df, features, binary_target, categorical_columns)
        evaluation_test_pool = Pool(X_test_std, label=y_test_std, group_id=group_ids_test, cat_features=categorical_columns)

        metrics = ranking_model.eval_metrics(
                evaluation_test_pool,
                metrics=[
                    "NDCG:top=5",
                    "PrecisionAt:top=5",
                    "RecallAt:top=5",
                    "MAP:top=5",
                    "MRR:top=5",
                    "ERR:top=5",
                    ]
            )

        self.repository.save_metrics(metrics, "metrics", f"{model_name}.json")

    def log_training_feature_evals(self, train_pool, ranking_model, features):
        importances = sorted(zip(features, ranking_model.get_feature_importance(data=train_pool)), key=lambda x: x[1], reverse=True)
        importances_logloss = sorted(zip(features, ranking_model.get_feature_importance(data=train_pool, type='LossFunctionChange')), key=lambda x: x[1], reverse=True)
        self.logger.info(f"[Training]: Feature Importance Prediction Change {importances}")
        self.logger.info(f"[Training]: Feature Importance Loss Function Change {importances_logloss}")
        self.logger.info(f"[Training]: Scale and Bias {ranking_model.get_scale_and_bias()}")
        self.logger.info(f"[Training]: Best Score {ranking_model.get_best_score()}")
        self.logger.info(f"[Training]: Best Iteration {ranking_model.get_best_iteration()}")

    def train(self):
        self.logger.info(f"[Training]: Starting Training...")

        hyperParameters = self.repository.get_hyperparameters("input/hyperparameters.json")
        df_train = self.repository.read("training.csv")
        df_test = self.repository.read("testing.csv")

        df_train = self.categorize_columns(df_train, self.GROUPINGS)
        df_test = self.categorize_columns(df_test, self.GROUPINGS)

        self.logger.info(f"[Training]: Categorical columns: {self.GROUPINGS}")
        self.logger.info(f"[Training]: Feature columns: {self.FULL_FEATURES}")
        self.logger.info(f"[Training]: Student Feature columns: {self.STUDENT_FEATURES}")

        X_train_std, y_train_std, group_ids_train = self.get_stds(df_train, self.FULL_FEATURES, self.TARGET_LABEL, self.GROUPINGS)
        X_test_std, y_test_std, group_ids_test = self.get_stds(df_test, self.FULL_FEATURES, self.TARGET_LABEL, self.GROUPINGS)

        train_pool = Pool(X_train_std, label=y_train_std, group_id=group_ids_train, cat_features=self.GROUPINGS, feature_names=self.FULL_FEATURES)
        test_pool = Pool(X_test_std, label=y_test_std, group_id=group_ids_test, cat_features=self.GROUPINGS, feature_names=self.FULL_FEATURES)

        for params in ParameterGrid(hyperParameters):

            model_prefix, ranking_model = self.train_with_params(train_pool, test_pool, params, 'teacher')
            self.log_training_feature_evals(train_pool, ranking_model, self.FULL_FEATURES)
            self.repository.save_models(ranking_model, f"model-{model_prefix}")
            self.evaluate_model(df_test, ranking_model, self.GROUPINGS, self.FULL_FEATURES, self.TARGET_LABEL, model_prefix)

            self.logger.debug(f"[Training]: Making predictions")
            y_pred_train = ranking_model.predict(train_pool)
            df_train[self.PREDICTION_LABEL] = X_train_std[self.PREDICTION_LABEL] = y_pred_train

            y_pred_test = ranking_model.predict(test_pool)
            df_test[self.PREDICTION_LABEL] = X_test_std[self.PREDICTION_LABEL] = y_pred_test

            self.repository.save(X_train_std, f"{model_prefix}_with_predictions.csv")
            self.repository.save(X_test_std, f"{model_prefix}_testing_with_predictions.csv")

            X_train_std[self.PREDICTION_LABEL] = pd.qcut(X_train_std[self.PREDICTION_LABEL], q=4, labels=False)
            X_test_std[self.PREDICTION_LABEL] = pd.qcut(X_test_std[self.PREDICTION_LABEL], q=4, labels=False)

            for student_params in ParameterGrid(hyperParameters):
                self.logger.debug(f"[Training]: X_train_std: \n {X_train_std.head()}")
                self.logger.debug(f"[Training]: X_test_std: \n {X_test_std.head()}")
                self.logger.debug(f"[Training]: X_test_std: \n {df_test.head()}")


                X_student_train_std, y_student_train_std, group_student_ids_train = self.get_stds(X_train_std, self.STUDENT_FEATURES, self.PREDICTION_LABEL, self.GROUPINGS)
                X_student_test_std, y_student_test_std, group_student_ids_test = self.get_stds(X_test_std, self.STUDENT_FEATURES, self.PREDICTION_LABEL, self.GROUPINGS)

                self.logger.debug(f"[Training]: Student X_train_std: \n {X_student_train_std.head()}")
                self.logger.debug(f"[Training]: Student X_test_std: \n {X_student_test_std.head()}")

                student_train_pool = Pool(X_student_train_std, label=y_student_train_std, group_id=group_student_ids_train, cat_features=self.GROUPINGS, feature_names=self.STUDENT_FEATURES)
                student_test_pool = Pool(X_student_test_std, label=y_student_test_std, group_id=group_student_ids_test, cat_features=self.GROUPINGS, feature_names=self.STUDENT_FEATURES)

                model_prefix, ranking_model = self.train_with_params(student_train_pool, student_test_pool, student_params, 'student')
                self.log_training_feature_evals(student_train_pool, ranking_model, self.STUDENT_FEATURES)
                self.repository.save_models(ranking_model, f"model-{model_prefix}")
                self.evaluate_model(df_test, ranking_model, self.GROUPINGS, self.STUDENT_FEATURES, self.PREDICTION_LABEL, model_prefix)


