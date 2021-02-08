# -*- coding: utf-8 -*-
"""robust_sleepnets.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ptrHB-fBl-DtnCp2S9qj0e7K-ICCX9IB

"""

import os
from PIL import Image
import numpy as np
from keras.models import Sequential
from keras.layers import Conv2D
from keras.layers import AveragePooling2D
from keras.layers import Flatten
from keras.layers import Dense
from keras.models import model_from_json
from keras.preprocessing.image import ImageDataGenerator
import matplotlib.pyplot as plt
import keras.backend as K

def collect_eye_generators(augment_data=False):
    # Setup non-augmented data parameters
    ROTATION_RANGE=0   
    WIDTH_SHIFT_RANGE=0
    HEIGHT_SHIFT_RANGE=0
    SHEAR_RANGE=0
    ZOOM_RANGE=0
    HORIZONTAL_FLIP=False

    if augment_data:
        ROTATION_RANGE=40      ## Adding these augment the training data
        WIDTH_SHIFT_RANGE=0.2  ## yields slightly lower accuracy values.
        HEIGHT_SHIFT_RANGE=0.2
        SHEAR_RANGE=0.2
        ZOOM_RANGE=0.2
        HORIZONTAL_FLIP=True
            
    IMG_SIZE = 24
    print("[INFO] loading images...")
    train_datagen = ImageDataGenerator(
		rotation_range=ROTATION_RANGE,    
		width_shift_range=WIDTH_SHIFT_RANGE, 
        height_shift_range=HEIGHT_SHIFT_RANGE,
        shear_range=SHEAR_RANGE,
        zoom_range=ZOOM_RANGE,
        horizontal_flip=HORIZONTAL_FLIP,
		rescale=1./255,
		validation_split=0.2)
    print("[INFO] Training data info:")
    train_generator = train_datagen.flow_from_directory(
	    directory="dataset/train-eye",
	    target_size=(IMG_SIZE, IMG_SIZE),
	    color_mode="grayscale",
	    batch_size=32,
	    class_mode="binary",
	    shuffle=True,
	    seed=42,
		subset='training'
	)

    print("[INFO] Validation data info:")
    val_generator = train_datagen.flow_from_directory(
	    directory="dataset/train-eye",
	    target_size=(IMG_SIZE, IMG_SIZE),
	    color_mode="grayscale",
	    batch_size=32,
	    class_mode="binary",
	    shuffle=True,
	    seed=42,
		subset='validation'
	)
	
    test_datagen = ImageDataGenerator(	
		  rescale=1./255,
	)
    print("[INFO] Testing data info:")
    test_generator = test_datagen.flow_from_directory(
        directory="dataset/test-eye",
        target_size=(IMG_SIZE, IMG_SIZE),
        color_mode="grayscale",
        shuffle = False,
        class_mode='binary',
        batch_size=1
	)

    return train_generator, val_generator, test_generator

def save_model(model, model_type):
    assert model_type in ["face", "eye"], "[INFO] Invalid input. Accepted inputs: 'eye' or 'face'"
    print("[INFO] Saving {} model".format(model_type))
    model_json = model.to_json()
    model_file_name = "model-{}".format(model_type)
    with open(model_file_name +".json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    model.save_weights(model_file_name + ".h5")

def determine_img_size_from_model_type(model_type):
    return 24 if model_type == 'eye' else 100

# custom metrics
def precision(y_true, y_pred): #taken from old keras source code
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision

def recall(y_true, y_pred): #taken from old keras source code
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall

def f1_score(y_true, y_pred):
    precision_result = precision(y_true, y_pred)
    recall_result = recall(y_true, y_pred)
    return 2*((precision_result*recall_result)/(precision_result+recall_result+K.epsilon()))

def load_model(model_type):
    assert model_type in ["face", "eye"], "[INFO] Invalid input. Accepted inputs: 'eye' or 'face'"
    print("[INFO] loading {} model".format(model_type))
    model_file_name = "model-{}".format(model_type)
    json_file = open(model_file_name + ".json", 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    # load weights into new model
    loaded_model.load_weights(model_file_name + ".h5")
    loaded_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy', precision, recall, f1_score])
    return loaded_model

def train(train_generator, val_generator, model_type):
    assert model_type in ["face", "eye"], "[INFO] Invalid input. Accepted inputs: 'eye' or 'face'"
    print("[INFO] Training {} model".format(model_type))
    STEP_SIZE_TRAIN=train_generator.n//train_generator.batch_size
    STEP_SIZE_VALID=val_generator.n//val_generator.batch_size

    print('[INFO] Initialize Neural Network')
    model = Sequential()
    IMG_SIZE = determine_img_size_from_model_type(model_type)

    model.add(Conv2D(filters=6, kernel_size=(3, 3), activation='relu', input_shape=(IMG_SIZE,IMG_SIZE,1)))
    model.add(AveragePooling2D())
    model.add(Conv2D(filters=16, kernel_size=(3, 3), activation='relu'))
    model.add(AveragePooling2D())
    model.add(Flatten())
    model.add(Dense(units=120, activation='relu'))
    model.add(Dense(units=84, activation='relu'))
    model.add(Dense(units=1, activation = 'sigmoid'))

    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy', precision, recall, f1_score])
    EPOCHS = 4
    print("[INFO] Training network for {} epochs...".format(EPOCHS))

    history = model.fit_generator(generator=train_generator,
                        steps_per_epoch=STEP_SIZE_TRAIN,
                        validation_data=val_generator,
                        validation_steps=STEP_SIZE_VALID,
                        epochs=EPOCHS)
 
    save_model(model, model_type)
    return history
    
def predict_single_image(img, model):
    img = Image.fromarray(img, 'RGB').convert('L')
    img = img.resize((IMG_SIZE,IMG_SIZE)).astype('float32')
    img /= 255
    img = img.reshape(1,IMG_SIZE,IMG_SIZE,1)
    prediction = model.predict(img)
    if prediction < 0.5:
        prediction = 'closed'
    elif prediction >= 0.5:
        prediction = 'open'
    return prediction

# Plot Accuracy and Loss
def plot_training_loss(history):
	# Plot training & validation accuracy values
	plt.plot(history.history['accuracy'])
	plt.plot(history.history['val_accuracy'])
	plt.title('Model accuracy')
	plt.ylabel('Accuracy')
	plt.xlabel('Epoch')
	plt.legend(['Train', 'Test'], loc='upper left')
	plt.show()

	# Plot training & validation loss values
	plt.plot(history.history['loss'])
	plt.plot(history.history['val_loss'])
	plt.title('Model loss')
	plt.ylabel('Loss')
	plt.xlabel('Epoch')
	plt.legend(['Train', 'Test'], loc='upper left')
	plt.show()

from sklearn.metrics import classification_report, confusion_matrix
def evaluate(test_generator, model_type):
    # evaluate the network
    model = load_model(model_type)
    print("[INFO] Evaluating network...")
    X_test, y_test = next(test_generator)
    score = model.evaluate(X_test, y_test, verbose = 0)
    print('Test loss:', score[0])
    print('Test accuracy:', score[1] * 100)
    print('Test precision:', score[2] * 100)
    print('Test recall:', score[3] * 100)
    print('Test f1_score:', score[4] * 100)

    
    predictions = model.predict(X_test) # predictions will be float numbers between
										# 0 and 1.
    predictions = (predictions > 0.5)    
    print(classification_report(y_test,
    predictions, target_names=['closed','open']))


import pandas as pd

def predict_with_generator(train_generator, test_generator, model_type):
    model = load_model(model_type)
    print("[INFO] Making predictions based on test dataset...")
    STEP_SIZE_TEST=test_generator.n//test_generator.batch_size
    test_generator.reset()
    pred=model.predict_generator(test_generator,
                                steps=STEP_SIZE_TEST,
                                verbose=1)
    pred[pred > 0.5] = 1
    pred[pred <= 0.5] = 0
    labels = (train_generator.class_indices)
    labels = dict((v,k) for k,v in labels.items())
    predictions = [labels[k[0]] for k in pred]
    filenames=test_generator.filenames
    results=pd.DataFrame({"Filename":filenames,
                        "Predictions":predictions})
    print("[INFO] Results:", results)
    print("[INFO] Predictions are completed. Results are written to csv.")
    results_csv_file_name = "results-{}.csv".format(model_type)
    results.to_csv(results_csv_file_name,index=False)

    #Confusion Matrix and Classification Report
    print('[INFO] Classification Report for model: {}'.format(model_type))
    print(classification_report(test_generator.classes,
    pred))

    print('[INFO] Confusion Matrix for model: {}'.format(model_type))
    print(confusion_matrix(test_generator.classes, pred))

# Create a TFLite Model for Mobile Applications
# This is useful because if we ever put the model into a moble device, we need a 
# model optimized and adapted for mobile applications. TFLite will help us in that. 
def create_tflite_model(model_type):
    assert model_type in ["face", "eye"], "[INFO] Invalid input. Accepted inputs: 'eye' or 'face'"
    with open('./model-{}.json'.format(model_type), 'r') as f:
        model = tf.keras.models.model_from_json(f.read())

    # Load weights into the new model
    model.load_weights('./model-{}.h5'.format(model_type))
    # Convert the model.
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    open("converted_model_{}.tflite".format(model_type), "wb").write(tflite_model);
    print('[INFO] Model {} is converted to TensorFlow Lite Model'.format(model_type))


# Display images
def display_images_from_dataset(model_type):
    import matplotlib.image as mpimg
    np.random.seed(123)
    X_train,y_train = train_generator.next()
    for i in range(0,10):
        # image = X_train[i]
        # print(train_generator.classes[i])
        # print(train_generator.filenames[i])
        # label = 'closed' if y_train[i]==0.0  else 'open' 
        # print('Label:', label)
        filename = np.random.choice(train_generator.filenames)
        p = os.path.join('dataset','train-{}'.format(model_type), filename)
        image = mpimg.imread(p)
        plt.imshow(image,cmap='gray');
        print(filename)
        plt.show()

def collect_face_generators(augment_data=False):
    IMG_SIZE = 100

    # Setup non-augmented data parameters
    ROTATION_RANGE=0   
    WIDTH_SHIFT_RANGE=0
    HEIGHT_SHIFT_RANGE=0
    SHEAR_RANGE=0
    ZOOM_RANGE=0
    HORIZONTAL_FLIP=False

    if augment_data:
        ROTATION_RANGE=40      ## Adding these augment the training data
        WIDTH_SHIFT_RANGE=0.2  ## yields slightly lower accuracy values.
        HEIGHT_SHIFT_RANGE=0.2
        SHEAR_RANGE=0.2
        ZOOM_RANGE=0.2
        HORIZONTAL_FLIP=True

    print("[INFO] loading images...")
    train_datagen = ImageDataGenerator(
		rotation_range=ROTATION_RANGE,    
		width_shift_range=WIDTH_SHIFT_RANGE, 
        height_shift_range=HEIGHT_SHIFT_RANGE,
        shear_range=SHEAR_RANGE,
        zoom_range=ZOOM_RANGE,
        horizontal_flip=HORIZONTAL_FLIP,
        fill_mode='nearest',
		rescale=1./255,
		validation_split=0.2)
    print("[INFO] Training data info:")
    train_generator = train_datagen.flow_from_directory(
	    directory="dataset/train-face",
	    target_size=(IMG_SIZE, IMG_SIZE),
	    color_mode="grayscale",
	    batch_size=32,
	    class_mode="binary",
	    shuffle=True,
	    seed=42,
		subset='training'
	)

    print("[INFO] Validation data info:")
    val_generator = train_datagen.flow_from_directory(
	    directory="dataset/train-face",
	    target_size=(IMG_SIZE, IMG_SIZE),
	    color_mode="grayscale",
	    batch_size=32,
	    class_mode="binary",
	    shuffle=True,
	    seed=42,
		subset='validation'
	)
	
    test_datagen = ImageDataGenerator(	
		  rescale=1./255,
	)
    print("[INFO] Testing data info:")
    test_generator = test_datagen.flow_from_directory(
        directory="dataset/test-face",
        target_size=(IMG_SIZE, IMG_SIZE),
        color_mode="grayscale",
        shuffle = False,
        class_mode='binary',
        batch_size=1
	)

    return train_generator, val_generator, test_generator

#########################################################
# Adversarial Attack Functions
#########################################################
import keras
from art.estimators.classification import KerasClassifier
from art.estimators.classification import TensorFlowClassifier
import tensorflow as tf
def generate_PGD_adversarial_attacks(train_generator, val_generator, model_type='face'):
    print("[INFO] Adversarial Attacking with PGD started...")
    model = load_model(model_type)
    
    tf.compat.v1.disable_eager_execution()
    tf.compat.v1.reset_default_graph()
    classifier = TensorFlowClassifier(model=model, clip_values=(0, 1))
    tf.compat.v1.reset_default_graph()
    # Create classifier wrapper
    print("[INFO] The Keras Classifier has {} classes".format(classifier.nb_classes))

    X_train, y_train = extract_x_y_data_from_generator(train_generator)
    X_test, y_test = extract_x_y_data_from_generator(val_generator)

    from art.attacks.evasion import ProjectedGradientDescent
    adv_crafter = ProjectedGradientDescent(classifier, eps=8, eps_step=7, max_iter=20, targeted=False, 
                                    num_random_init=False)

    X_train_adv = adv_crafter.generate(X_train)
    X_test_adv = adv_crafter.generate(X_test)


    y_test = keras.utils.to_categorical(y_test, 2)

    # Evaluate the classifier on the adversarial samples
    preds = np.argmax(model.predict(X_test_adv), axis=1)
    acc = np.sum(preds == np.argmax(y_test, axis=1)) / y_test.shape[0]
    print("[INFO] Accuracy on PGD adversarial samples: {:.2f}".format(acc * 100))
    return X_train_adv, y_train, X_test_adv, y_test


# Adversarially train the classifier on the adversarial samples
def adversarial_train(X_train_adv, y_train, model_type='face'):
    print("[INFO] Adversarial training started...")
    model = load_model(model_type)
    
    print("len(X_train_adv)",len(X_train_adv))
    print("len(y_train)",len(y_train))
    # https://stackoverflow.com/questions/56912176/target-array-shape-different-to-expected-output-using-tensorflow
    history = model.fit(X_train_adv, y_train, validation_split=0.2, epochs=10, batch_size=5, verbose=1)
    
    print("[INFO] Adversarial training finished")
    print(history.history)
    plot_training_loss(history)
    return model

def extract_x_y_data_from_generator(gen):
    #  max_iter: maximum number of iterations, in each iteration one batch is generated; the proper value depends on batch size and size of whole data
    data = []     # store all the generated data batches
    labels = []   # store all the generated label batches
    i = 0
    max_iter = len(gen.filenames) # get maximum iteration count from file list in the generator
    for d, l in test_generator:
        data.append(d[0])
        labels.append(l[0])
        i += 1
        if i == max_iter:
            break

    X_test = data
    y_test = labels 
    print("Data size: {}".format(len(X_test)))
    return np.array(X_test),np.array(y_test)

def evaluate_adversarially_trained_model(adversarially_trained_model, X_test_adv, y_test):
    print("[INFO] X data size: {:.2f}".format(len(X_test_adv)))
    print("[INFO] y data size: {:.2f}".format(len(y_test)))
    preds = np.argmax(adversarially_trained_model.predict(X_test_adv), axis=1)
    acc = np.sum(preds == np.argmax(y_test, axis=1)) / y_test.shape[0]
    print("[INFO] Accuracy on adversarial samples: {:.2f}".format(acc * 100))


def run_pipeline_for_PGD(train_generator, val_generator, model_type='face'):
    # Generate adversarial attacks
    X_train_adv, y_train, X_test_adv, y_test = generate_PGD_adversarial_attacks(train_generator, val_generator, model_type)
    # Use the attacks to adversarially train the model
    adversarially_trained_model = adversarial_train(X_train_adv, y_train, model_type)
    # Evaluate the classifier on the adversarial samples
    evaluate_adversarially_trained_model(adversarially_trained_model, X_test_adv, y_test)
    # Original classifier results
    predict_with_generator(train_generator, test_generator, model_type)

def generate_FGSM_adversarial_attacks(train_generator, val_generator, model_type='face'):
    print("[INFO] Adversarial Attacking with FGSM started...")
    # Craft adversarial samples with FGSM
    model = load_model(model_type)
    tf.compat.v1.disable_eager_execution()
    tf.compat.v1.reset_default_graph()
    classifier = KerasClassifier(model=model, clip_values=(0, 1))
    tf.compat.v1.reset_default_graph()
    # Create classifier wrapper
    print("[INFO] The Keras Classifier has {} classes".format(classifier.nb_classes))

    X_train, y_train = extract_x_y_data_from_generator(train_generator)
    X_test, y_test = extract_x_y_data_from_generator(val_generator)

    from art.attacks.evasion import FastGradientMethod
    adv_crafter = FastGradientMethod(classifier, eps=0.1, targeted=False)

    X_train_adv = adv_crafter.generate(X_train)
    X_test_adv = adv_crafter.generate(X_test)


    y_test = keras.utils.to_categorical(y_test, 2)

    # Evaluate the classifier on the adversarial samples
    preds = np.argmax(model.predict(X_test_adv), axis=1)
    acc = np.sum(preds == np.argmax(y_test, axis=1)) / y_test.shape[0]
    print("[INFO] Accuracy on FGSM adversarial samples: {:.2f}".format(acc * 100))
    return X_train_adv, y_train, X_test_adv, y_test



def run_pipeline_for_FGSM(train_generator, val_generator, model_type='face'):
    print("[INFO] Pipeline for FGSM started")
    # Generate adversarial attacks
    X_train_adv, y_train, X_test_adv, y_test = generate_FGSM_adversarial_attacks(train_generator,val_generator, model_type)
    # Use the attacks to adversarially train the model
    adversarially_trained_model = adversarial_train(X_train_adv, y_train, model_type)
    # Evaluate the classifier on the adversarial samples
    evaluate_adversarially_trained_model(adversarially_trained_model, X_test_adv, y_test)
    # Original classifier results
    predict_with_generator(train_generator, test_generator, model_type)
    print("[INFO] Pipeline for FGSM finished")

"""# Eye Image Model - No data augmentation"""

train_generator , val_generator, test_generator = collect_eye_generators()
history = train(train_generator,val_generator, model_type="eye")
plot_training_loss(history)
eye_model = load_model('eye')
print(eye_model.summary())
predict_with_generator(train_generator, test_generator, model_type="eye")
evaluate(val_generator, model_type="eye")
# evaluate(val_generator, model_type="eye")
run_pipeline_for_PGD(train_generator, val_generator, 'eye')
# run_pipeline_for_FGSM(train_generator, val_generator, model_type='eye')

# run_pipeline_for_PGD(train_generator, val_generator, model_type='eye')
# run_pipeline_for_FGSM(train_generator, val_generator, model_type='eye')

"""# Eye Model - With Data Augmentation"""

# train_generator , val_generator, test_generator = collect_eye_generators(True) # Set augment_data to True
# history = train(train_generator,val_generator, model_type="eye")
# plot_training_loss(history)
# eye_model = load_model('eye')
# print(eye_model.summary())
# predict_with_generator(train_generator, test_generator, model_type="eye")
# run_pipeline_for_PGD(train_generator, val_generator, 'eye')
# run_pipeline_for_FGSM(train_generator, val_generator, model_type='eye')

"""# Facial Image Model No Data Augmentation


"""

# train_generator , val_generator, test_generator = collect_face_generators()
# history = train(train_generator,val_generator, model_type="face")
# plot_training_loss(history)
# face_model = load_model('face')
# print(face_model.summary())
# predict_with_generator(train_generator, test_generator, model_type="face")
# evaluate(val_generator, model_type="face")
# run_pipeline_for_PGD(train_generator, val_generator, 'face')
# run_pipeline_for_FGSM(train_generator, val_generator, model_type='face')

"""# Face Model - With Data Augmentation"""

# train_generator , val_generator, test_generator = collect_face_generators(True) # Set augment_data to True 
# history = train(train_generator,val_generator, model_type="face")
# plot_training_loss(history)
# face_model = load_model('face')
# print(face_model.summary())
# predict_with_generator(train_generator, test_generator, model_type="face")
# evaluate(val_generator, model_type="face")
# run_pipeline_for_PGD(train_generator, val_generator, 'face')
# run_pipeline_for_FGSM(train_generator, val_generator, model_type='face')
