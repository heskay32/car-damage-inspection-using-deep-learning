from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from carinspection.models import PicUpload
from carinspection.forms import ImageForm

# Create your views here.
def index(request):
	return render(request, 'carinspection/index.html')

def analysis(request):
	return render(request, 'carinspection/analysis.html')

def about(request):
	return render(request, 'carinspection/about.html')


def start(request):
	image_path = ''
	image_path1 = ''
	if request.method == 'POST':
		form = ImageForm(request.POST, request.FILES)
		if form.is_valid():
			newdoc = PicUpload(imagefile=request.FILES['imagefile'])
			newdoc.save()
			return HttpResponseRedirect(reverse('start'))

	else:
		form = ImageForm()
	documents = PicUpload.objects.all()
	for document in documents:
		image_path = document.imagefile.name
		image_path1 = '/'+image_path

		document.delete()
	request.session['image_path'] = image_path
	return render(request, 'carinspection/start.html',
	{'documents':documents, 'image_path1':image_path1, 'form':form}
	)





#*******************Car Damage Inspection***********

#import libraries
import os
import json
import h5py
import numpy as np
import pickle as pk
from PIL import Image

#Keras imports
from keras.models import load_model, Model
from keras.utils import img_to_array, load_img
from keras.applications.vgg16 import VGG16
from keras.applications.imagenet_utils import preprocess_input
from keras.preprocessing import image
from keras import backend as k
import tensorflow as tf

#prepare image for preprocessing
def prepare_img(img_path):
	img = load_img(img_path, target_size=(224,224))
	x = img_to_array(img)
	x = np.expand_dims(x, axis=0)
	x = preprocess_input(x)
	return x

#load labels for identifying cars using vgg16
with open('static/label_counter.pk', 'rb') as f:
	label_counter = pk.load(f)

#shortlist top 25 labels stored by vgg16
label_list = [k for k,v in label_counter.most_common()[:25]]

global graph
graph = tf.compat.v1.get_default_graph()

#preprocess and flatten image
def prepare_flat(img_224):
	base_model = load_model('static/vgg16.h5')
	model = Model(base_model.input, base_model.get_layer('fc1').output)
	feature = model.predict(img_224)
	flat = feature.flatten()
	flat = np.expand_dims(flat, axis=0)
	return flat

#load Models, class and weights
CLASS_INDEX_PATH = 'static/imagenet_class_index.json'

def get_predictions(preds, top=5):
	global CLASS_INDEX
	CLASS_INDEX = json.load(open(CLASS_INDEX_PATH))

	results = []
	for pred in preds:
		top_indices = pred.argsort()[-top:][::-1]
		result = [tuple(CLASS_INDEX[str(i)]) + (pred[i],) for i in top_indices]
		result.sort(key=lambda x: x[2], reverse=True)
		results.append(result)
	return results


#First Check
def car_categories_check(img_224):
	first_check = load_model('static/vgg16.h5')
	print('Validating if the picture is of a Car...')
	out = first_check.predict(img_224)
	top = get_predictions(out, top=5)
	for j in top[0]:
		if j[0:2] in label_list:
			print('\nCar Check Passed!!!\n')
			return True
	return False


#Second Check
def car_damage_check(img_flat):
	second_check = pk.load(open('static/second_check.pickle', 'rb'))
	print('Validating if there is damage...')
	train_labels = ['Car is Damaged', 'Car is not Damaged']
	preds = second_check.predict(img_flat)
	prediction = train_labels[preds[0]]

	if train_labels[preds[0]]=='Car is Damaged':
		print('\n=>> Damage Check Passed!!! - Proceeding to damage location and severity detection\n')
		return True
	else:
		return False


#Third Check
def location_assesement(img_flat):
	third_check = pk.load(open('static/third_check.pickle', 'rb'))
	print('Validating damage location...')
	train_labels = ['Front', 'Rare', 'Side']
	preds = third_check.predict(img_flat)
	prediction = train_labels[preds[0]]
	print('\n~Your car is damaged at the ', train_labels[preds[0]])
	print('\n')
	print('=>> Damage location Passed!!! - Proceeding to severity detection\n')
	return prediction


#Fourth Check
def severity_assesement(img_flat):
	fourth_check = pk.load(open('static/fourth_check.pickle', 'rb'))
	print('Validating the severity of damage...')
	train_labels = ['Minor', 'Moderate', 'Severe']
	preds = fourth_check.predict(img_flat)
	prediction = train_labels[preds[0]]
	print('\n~Your car Damage is ', train_labels[preds[0]])
	print('\n=>>All Checks complete')
	print('\nThank you for using this service.')
	return prediction



#Integrate All Checks

def engine(request):

	MyCar = request.session['image_path']
	img_path = MyCar
	request.session.pop('image_path', None)
	request.session.modified = True
	with graph.as_default():

		img_224 = prepare_img(img_path)
		img_flat = prepare_flat(img_224)
		c1 = car_categories_check(img_224)
		c2 = car_damage_check(img_flat)

		while True:
			try:
				if c1 is False:
					c1_pic = 'Image does not look like a picture of a car, please submit another picture of your damaged car.'
					c2_pic = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					c3 = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					c4 = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					ns = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					break
				else:
					c1_pic = '<i class="fa-solid fa-circle-check fa-1xl"></i>'

				if c2 is False:
					c2_pic = 'Are you sure this car is damaged? Please submit another picture of your damaged car.'
					c3 = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					c4 = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					ns = '<i class="fa-solid fa-circle-xmark fa-1xl"></i>'
					break
				else:
					c2_pic = '<i class="fa-solid fa-circle-check fa-1xl"></i>'
					c3 = location_assesement(img_flat)
					c4 = severity_assesement(img_flat)
					ns = 'a). Create a report and send to vendor \n b). Proceed to cost estimation'
					break
			except:
				break

	src = 'pic_upload/'
	import os
	for image_file_name in os.listdir(src):
		if image_file_name.endswith('.jpg'):
			os.remove(src + image_file_name)
	k.clear_session()

	context={'c1_pic':c1_pic, 'c2_pic':c2_pic, 'loc':c3, 'sev':c4, 'ns':ns}
	results = json.dumps(context)
	return HttpResponse(results, content_type = 'application/json')




