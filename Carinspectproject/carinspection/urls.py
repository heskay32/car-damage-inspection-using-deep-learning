from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name = 'home'),
	path('start/', views.start, name = 'start'),
	path('engine/', views.engine, name = 'engine'),
	path('analysis/', views.analysis, name = 'analysis'),
	path('about/', views.about, name = 'about'),
]