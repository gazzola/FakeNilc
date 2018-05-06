import argparse
import sys
import logging
from sklearn.model_selection import cross_val_predict, train_test_split
from sklearn.metrics import classification_report , confusion_matrix, accuracy_score
from sklearn.utils import shuffle
from sklearn.svm import SVC, LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
import pandas as pd 
import numpy as np


#TODO: add logging system, and remove prints

def prepareArgParser():
	choices = ['svc','linearsvc','naive_bayes','randomforest', 'all', 'mlp']

	arg_parser = argparse.ArgumentParser(description='A fake news classifier training system')
	arg_parser.add_argument('dataset_filenames', help='path to the files used as datasets.', nargs='+')
	arg_parser.add_argument('--n_jobs', help='number of threads to use when cross validating', type=int, default=2)
	arg_parser.add_argument('-v','--verbose', help='output verbosity.', action='store_true')
	arg_parser.add_argument('-d','--debug', help='output debug messages', action='store_true')
	arg_parser.add_argument('-lc','--learning_curve_steps', help='no. of percentages used in learning curve. If -1, the learning curve is not calculated (default)', type=int, default=1)
	arg_parser.add_argument('-o','--output', help='output filename', type=argparse.FileType('w', encoding='UTF-8'), default='-')
	arg_parser.add_argument('-c','--classifier', help='Specific classifier to be used. If ommited, uses all classifiers except for MLPClassifier', choices=choices)
	return arg_parser


def parseArguments():

	arg_parser = prepareArgParser()
	args = arg_parser.parse_args()

	### Parameters
	flags = {}
	#dataset filename
	dataset_filenames = args.dataset_filenames
	#verbosity
	flags['v'] = (args.verbose or args.debug)
	#debug verbosity
	flags['d'] = args.debug
	#paralelism level used in cross validation
	flags['n_jobs'] = args.n_jobs if args.n_jobs else 2
	#no. of percentages used in learning curve
	flags['lc'] = args.learning_curve_steps
	#output file
	output = args.output

	#classifiers used. if 'all' or None, uses all classifiers
	classifier = [LinearSVC(),
					  MultinomialNB(),
					  RandomForestClassifier()
					  ]
	if args.classifier == 'linearsvc':
		classifier = [classifier[0]]
	elif args.classifier == 'naive_bayes':
		classifier = [classifier[1]]
	elif args.classifier == 'randomforest':
		classifier = [classifier[2]]
	elif args.classifier == 'mlp':
		classifier = [MLPClassifier()]
	else:
		pass #all classifiers except mlp are already set

	return (dataset_filenames, flags, output, classifier)


def getDatasetValues(df):
	# Getting the tags column and saving it into y
	y = df.loc[:,'Tag'].tolist()
	# Dropping the column with tags
	df = df.drop('Tag',axis=1)

	# X contain a matrix with dataframe values, y contains a 
	X = df.values

	# Id Contain Indexes
	Id = df.index.values

	#shuffling dataset
	X, y, Id = shuffle(X, y, Id)

	return (X, y, Id)


def predictAndEvaluate(classifier, X, y, lc = 5,  n_jobs = 2, verbose = False):

	logger = logging.getLogger(__name__)

	#calculating slices of the dataset
	s = (np.linspace(0,1,lc+1) * len(y)).astype(np.int)[1:] #creates an array from 0.1 to 1 with 10 evenly spaced items, and multiply by the number of instances of the dataset

	predicts = []
	for val in s:
		logger.info('cross evaluating with '+ str((val/len(y))*100) + '% of corpus')
		predicts.append( cross_val_predict(classifier, X[:val], y[:val], cv=5, verbose=verbose, n_jobs=n_jobs) )

	return predicts


def printResults(classifier, real, predicts, f = sys.stdout):

	logger = logging.getLogger(__name__)

	#printing classification report
	print('Classifier:', classifier, file=f)
	print(classification_report(real,predicts[-1]), file = f)

	#printing confusion matrix
	tn, fp, fn, tp = confusion_matrix(real, predicts[-1]).ravel()
	print('Confusion Matrix:', file = f)
	print(' a      b     <--- Classified as', file = f)
	print('{0:5d}  {1:5d}   a = REAL'.format(tp,fp), file = f)
	print('{0:5d}  {1:5d}   b = FAKE\n'.format(fn,tn), file = f)
	print(file=f)

	if len(predicts) > 1:
		p = np.linspace(0,1,len(predicts)+1)[1:] #percentages
		# logger.debug(p)
		s = (p * len(real)).astype(np.int) #dataset sizes
		#calculating accuracy score for each prediction
		scores = [ accuracy_score(real[:s[i]], predicts[i]) for i in range(len(predicts)) ]
		print('Learning curve:',file=f)
		print(scores,file=f)


def main():

	#parsing arguments from command line
	dataset_filenames, flags, output, classifiers = parseArguments()
	
	#setting verbosity level to python logger
	logging.basicConfig()
	logger = logging.getLogger(__name__)
	if flags['v']: logger.setLevel(logging.INFO) 
	if flags['d']: logger.setLevel(logging.DEBUG) 

	# for each file in the dataset files
	for dataset_filename in dataset_filenames:
		print('Dataset:', dataset_filename, file=output)

		#loads the dataset into a pandas dataframe
		logger.info('Loading dataset ' + dataset_filename)
		df = pd.read_csv(dataset_filename, encoding='utf8', index_col=0)

		#split the dataframe in X(data) and y(labels)
		logger.info('Splitting labels and data...')
		X, y, Ids = getDatasetValues(df)

		predicts = []
		#trains and evaluate each classifier described in classifiers
		for clf in classifiers:

			logger.info('Evaluating ' + clf.__class__.__name__)

			#predicts is a list with lists of labels classified in a 5-fold cross validation evaluation of the classifiers
			#each value in predicts represents a percentage of the dataset used for validation
			#i.e. if predicts contains 3 items, then p[0] used 33% p[1] used 66% and p[2] used 100% of the dataset for evaluation
			predicts = predictAndEvaluate(clf, X, y, flags['lc'] , flags['n_jobs'], flags['v'])

			logger.info('Printing Results')
			printResults(clf.__class__.__name__, y, predicts, f=output)

			#After evaluating, deletes the used classifier
			del clf
		print('==============',file=output)

		missed = [Ids[i] + ' Classified as ' + predicts[-1][i] + '\n' for i in range(len(y)) if predicts[-1][i] != y[i] ]
		print(*missed, file = output)

	logger.info('Done')


if __name__ == '__main__':
	main()