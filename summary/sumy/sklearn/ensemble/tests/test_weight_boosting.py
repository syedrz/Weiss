"""Testing for the boost module (sklearn.ensemble.boost)."""

import numpy as np
from sklearn.utils.testing import assert_array_equal, assert_array_less
from sklearn.utils.testing import assert_array_almost_equal
from sklearn.utils.testing import assert_equal
from sklearn.utils.testing import assert_raises, assert_raises_regexp

from sklearn.cross_validation import train_test_split
from sklearn.grid_search import GridSearchCV
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import AdaBoostRegressor
from scipy.sparse import csc_matrix
from scipy.sparse import csr_matrix
from scipy.sparse import coo_matrix
from scipy.sparse import dok_matrix
from scipy.sparse import lil_matrix
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.utils import shuffle
from sklearn import datasets


# Common random state
rng = np.random.RandomState(0)

# Toy sample
X = [[-2, -1], [-1, -1], [-1, -2], [1, 1], [1, 2], [2, 1]]
y_class = ["foo", "foo", "foo", 1, 1, 1]    # test string class labels
y_regr = [-1, -1, -1, 1, 1, 1]
T = [[-1, -1], [2, 2], [3, 2]]
y_t_class = ["foo", 1, 1]
y_t_regr = [-1, 1, 1]

# Load the iris dataset and randomly permute it
iris = datasets.load_iris()
perm = rng.permutation(iris.target.size)
iris.data, iris.target = shuffle(iris.data, iris.target, random_state=rng)

# Load the boston dataset and randomly permute it
boston = datasets.load_boston()
boston.data, boston.target = shuffle(boston.data, boston.target,
                                     random_state=rng)


def test_classification_toy():
    # Check classification on a toy dataset.
    for alg in ['SAMME', 'SAMME.R']:
        clf = AdaBoostClassifier(algorithm=alg, random_state=0)
        clf.fit(X, y_class)
        assert_array_equal(clf.predict(T), y_t_class)
        assert_array_equal(np.unique(np.asarray(y_t_class)), clf.classes_)
        assert_equal(clf.predict_proba(T).shape, (len(T), 2))
        assert_equal(clf.decision_function(T).shape, (len(T),))


def test_regression_toy():
    # Check classification on a toy dataset.
    clf = AdaBoostRegressor(random_state=0)
    clf.fit(X, y_regr)
    assert_array_equal(clf.predict(T), y_t_regr)


def test_iris():
    # Check consistency on dataset iris.
    classes = np.unique(iris.target)
    clf_samme = prob_samme = None

    for alg in ['SAMME', 'SAMME.R']:
        clf = AdaBoostClassifier(algorithm=alg)
        clf.fit(iris.data, iris.target)

        assert_array_equal(classes, clf.classes_)
        proba = clf.predict_proba(iris.data)
        if alg == "SAMME":
            clf_samme = clf
            prob_samme = proba
        assert_equal(proba.shape[1], len(classes))
        assert_equal(clf.decision_function(iris.data).shape[1], len(classes))

        score = clf.score(iris.data, iris.target)
        assert score > 0.9, "Failed with algorithm %s and score = %f" % \
            (alg, score)

    # Somewhat hacky regression test: prior to
    # ae7adc880d624615a34bafdb1d75ef67051b8200,
    # predict_proba returned SAMME.R values for SAMME.
    clf_samme.algorithm = "SAMME.R"
    assert_array_less(0,
                      np.abs(clf_samme.predict_proba(iris.data) - prob_samme))


def test_boston():
    # Check consistency on dataset boston house prices.
    clf = AdaBoostRegressor(random_state=0)
    clf.fit(boston.data, boston.target)
    score = clf.score(boston.data, boston.target)
    assert score > 0.85


def test_staged_predict():
    # Check staged predictions.
    rng = np.random.RandomState(0)
    iris_weights = rng.randint(10, size=iris.target.shape)
    boston_weights = rng.randint(10, size=boston.target.shape)

    # AdaBoost classification
    for alg in ['SAMME', 'SAMME.R']:
        clf = AdaBoostClassifier(algorithm=alg, n_estimators=10)
        clf.fit(iris.data, iris.target, sample_weight=iris_weights)

        predictions = clf.predict(iris.data)
        staged_predictions = [p for p in clf.staged_predict(iris.data)]
        proba = clf.predict_proba(iris.data)
        staged_probas = [p for p in clf.staged_predict_proba(iris.data)]
        score = clf.score(iris.data, iris.target, sample_weight=iris_weights)
        staged_scores = [
            s for s in clf.staged_score(
                iris.data, iris.target, sample_weight=iris_weights)]

        assert_equal(len(staged_predictions), 10)
        assert_array_almost_equal(predictions, staged_predictions[-1])
        assert_equal(len(staged_probas), 10)
        assert_array_almost_equal(proba, staged_probas[-1])
        assert_equal(len(staged_scores), 10)
        assert_array_almost_equal(score, staged_scores[-1])

    # AdaBoost regression
    clf = AdaBoostRegressor(n_estimators=10, random_state=0)
    clf.fit(boston.data, boston.target, sample_weight=boston_weights)

    predictions = clf.predict(boston.data)
    staged_predictions = [p for p in clf.staged_predict(boston.data)]
    score = clf.score(boston.data, boston.target, sample_weight=boston_weights)
    staged_scores = [
        s for s in clf.staged_score(
            boston.data, boston.target, sample_weight=boston_weights)]

    assert_equal(len(staged_predictions), 10)
    assert_array_almost_equal(predictions, staged_predictions[-1])
    assert_equal(len(staged_scores), 10)
    assert_array_almost_equal(score, staged_scores[-1])


def test_gridsearch():
    # Check that base trees can be grid-searched.
    # AdaBoost classification
    boost = AdaBoostClassifier(base_estimator=DecisionTreeClassifier())
    parameters = {'n_estimators': (1, 2),
                  'base_estimator__max_depth': (1, 2),
                  'algorithm': ('SAMME', 'SAMME.R')}
    clf = GridSearchCV(boost, parameters)
    clf.fit(iris.data, iris.target)

    # AdaBoost regression
    boost = AdaBoostRegressor(base_estimator=DecisionTreeRegressor(),
                              random_state=0)
    parameters = {'n_estimators': (1, 2),
                  'base_estimator__max_depth': (1, 2)}
    clf = GridSearchCV(boost, parameters)
    clf.fit(boston.data, boston.target)


def test_pickle():
    # Check pickability.
    import pickle

    # Adaboost classifier
    for alg in ['SAMME', 'SAMME.R']:
        obj = AdaBoostClassifier(algorithm=alg)
        obj.fit(iris.data, iris.target)
        score = obj.score(iris.data, iris.target)
        s = pickle.dumps(obj)

        obj2 = pickle.loads(s)
        assert_equal(type(obj2), obj.__class__)
        score2 = obj2.score(iris.data, iris.target)
        assert_equal(score, score2)

    # Adaboost regressor
    obj = AdaBoostRegressor(random_state=0)
    obj.fit(boston.data, boston.target)
    score = obj.score(boston.data, boston.target)
    s = pickle.dumps(obj)

    obj2 = pickle.loads(s)
    assert_equal(type(obj2), obj.__class__)
    score2 = obj2.score(boston.data, boston.target)
    assert_equal(score, score2)


def test_importances():
    # Check variable importances.
    X, y = datasets.make_classification(n_samples=2000,
                                        n_features=10,
                                        n_informative=3,
                                        n_redundant=0,
                                        n_repeated=0,
                                        shuffle=False,
                                        random_state=1)

    for alg in ['SAMME', 'SAMME.R']:
        clf = AdaBoostClassifier(algorithm=alg)

        clf.fit(X, y)
        importances = clf.feature_importances_

        assert_equal(importances.shape[0], 10)
        assert_equal((importances[:3, np.newaxis] >= importances[3:]).all(),
                     True)


def test_error():
    # Test that it gives proper exception on deficient input.
    assert_raises(ValueError,
                  AdaBoostClassifier(learning_rate=-1).fit,
                  X, y_class)

    assert_raises(ValueError,
                  AdaBoostClassifier(algorithm="foo").fit,
                  X, y_class)

    assert_raises(ValueError,
                  AdaBoostClassifier().fit,
                  X, y_class, sample_weight=np.asarray([-1]))


def test_base_estimator():
    # Test different base estimators.
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.svm import SVC

    # XXX doesn't work with y_class because RF doesn't support classes_
    # Shouldn't AdaBoost run a LabelBinarizer?
    clf = AdaBoostClassifier(RandomForestClassifier())
    clf.fit(X, y_regr)

    clf = AdaBoostClassifier(SVC(), algorithm="SAMME")
    clf.fit(X, y_class)

    from sklearn.ensemble import RandomForestRegressor
    from sklearn.svm import SVR

    clf = AdaBoostRegressor(RandomForestRegressor(), random_state=0)
    clf.fit(X, y_regr)

    clf = AdaBoostRegressor(SVR(), random_state=0)
    clf.fit(X, y_regr)

    # Check that an empty discrete ensemble fails in fit, not predict.
    X_fail = [[1, 1], [1, 1], [1, 1], [1, 1]]
    y_fail = ["foo", "bar", 1, 2]
    clf = AdaBoostClassifier(SVC(), algorithm="SAMME")
    assert_raises_regexp(ValueError, "worse than random",
                         clf.fit, X_fail, y_fail)


def test_sample_weight_missing():
    from sklearn.linear_model import LinearRegression
    from sklearn.cluster import KMeans

    clf = AdaBoostClassifier(LinearRegression(), algorithm="SAMME")
    assert_raises(ValueError, clf.fit, X, y_regr)

    clf = AdaBoostRegressor(LinearRegression())
    assert_raises(ValueError, clf.fit, X, y_regr)

    clf = AdaBoostClassifier(KMeans(), algorithm="SAMME")
    assert_raises(ValueError, clf.fit, X, y_regr)

    clf = AdaBoostRegressor(KMeans())
    assert_raises(ValueError, clf.fit, X, y_regr)


def test_sparse_classification():
    # Check classification with sparse input.

    class CustomSVC(SVC):
        """SVC variant that records the nature of the training set."""

        def fit(self, X, y, sample_weight=None):
            """Modification on fit caries data type for later verification."""
            super(CustomSVC, self).fit(X, y, sample_weight=sample_weight)
            self.data_type_ = type(X)
            return self

    X, y = datasets.make_multilabel_classification(n_classes=1, n_samples=15,
                                                   n_features=5,
                                                   return_indicator=True,
                                                   random_state=42)
    # Flatten y to a 1d array
    y = np.ravel(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)

    for sparse_format in [csc_matrix, csr_matrix, lil_matrix, coo_matrix,
                          dok_matrix]:
        X_train_sparse = sparse_format(X_train)
        X_test_sparse = sparse_format(X_test)

        # Trained on sparse format
        sparse_classifier = AdaBoostClassifier(
            base_estimator=CustomSVC(probability=True),
            random_state=1,
            algorithm="SAMME"
        ).fit(X_train_sparse, y_train)

        # Trained on dense format
        dense_classifier = AdaBoostClassifier(
            base_estimator=CustomSVC(probability=True),
            random_state=1,
            algorithm="SAMME"
        ).fit(X_train, y_train)

        # predict
        sparse_results = sparse_classifier.predict(X_test_sparse)
        dense_results = dense_classifier.predict(X_test)
        assert_array_equal(sparse_results, dense_results)

        # decision_function
        sparse_results = sparse_classifier.decision_function(X_test_sparse)
        dense_results = dense_classifier.decision_function(X_test)
        assert_array_equal(sparse_results, dense_results)

        # predict_log_proba
        sparse_results = sparse_classifier.predict_log_proba(X_test_sparse)
        dense_results = dense_classifier.predict_log_proba(X_test)
        assert_array_equal(sparse_results, dense_results)

        # predict_proba
        sparse_results = sparse_classifier.predict_proba(X_test_sparse)
        dense_results = dense_classifier.predict_proba(X_test)
        assert_array_equal(sparse_results, dense_results)

        # score
        sparse_results = sparse_classifier.score(X_test_sparse, y_test)
        dense_results = dense_classifier.score(X_test, y_test)
        assert_array_equal(sparse_results, dense_results)

        # staged_decision_function
        sparse_results = sparse_classifier.staged_decision_function(
            X_test_sparse)
        dense_results = dense_classifier.staged_decision_function(X_test)
        for sprase_res, dense_res in zip(sparse_results, dense_results):
            assert_array_equal(sprase_res, dense_res)

        # staged_predict
        sparse_results = sparse_classifier.staged_predict(X_test_sparse)
        dense_results = dense_classifier.staged_predict(X_test)
        for sprase_res, dense_res in zip(sparse_results, dense_results):
            assert_array_equal(sprase_res, dense_res)

        # staged_predict_proba
        sparse_results = sparse_classifier.staged_predict_proba(X_test_sparse)
        dense_results = dense_classifier.staged_predict_proba(X_test)
        for sprase_res, dense_res in zip(sparse_results, dense_results):
            assert_array_equal(sprase_res, dense_res)

        # staged_score
        sparse_results = sparse_classifier.staged_score(X_test_sparse,
                                                        y_test)
        dense_results = dense_classifier.staged_score(X_test, y_test)
        for sprase_res, dense_res in zip(sparse_results, dense_results):
            assert_array_equal(sprase_res, dense_res)

        # Verify sparsity of data is maintained during training
        types = [i.data_type_ for i in sparse_classifier.estimators_]

        assert all([(t == csc_matrix or t == csr_matrix)
                   for t in types])


def test_sparse_regression():
    # Check regression with sparse input.

    class CustomSVR(SVR):
        """SVR variant that records the nature of the training set."""

        def fit(self, X, y, sample_weight=None):
            """Modification on fit caries data type for later verification."""
            super(CustomSVR, self).fit(X, y, sample_weight=sample_weight)
            self.data_type_ = type(X)
            return self

    X, y = datasets.make_regression(n_samples=15, n_features=50, n_targets=1,
                                    random_state=42)

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)

    for sparse_format in [csc_matrix, csr_matrix, lil_matrix, coo_matrix,
                          dok_matrix]:
        X_train_sparse = sparse_format(X_train)
        X_test_sparse = sparse_format(X_test)

        # Trained on sparse format
        sparse_classifier = AdaBoostRegressor(
            base_estimator=CustomSVR(),
            random_state=1
        ).fit(X_train_sparse, y_train)

        # Trained on dense format
        dense_classifier = dense_results = AdaBoostRegressor(
            base_estimator=CustomSVR(),
            random_state=1
        ).fit(X_train, y_train)

        # predict
        sparse_results = sparse_classifier.predict(X_test_sparse)
        dense_results = dense_classifier.predict(X_test)
        assert_array_equal(sparse_results, dense_results)

        # staged_predict
        sparse_results = sparse_classifier.staged_predict(X_test_sparse)
        dense_results = dense_classifier.staged_predict(X_test)
        for sprase_res, dense_res in zip(sparse_results, dense_results):
            assert_array_equal(sprase_res, dense_res)

        types = [i.data_type_ for i in sparse_classifier.estimators_]

        assert all([(t == csc_matrix or t == csr_matrix)
                   for t in types])
