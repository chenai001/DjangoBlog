# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django import forms
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from tagging.models import Tag    ##
from tagging.fields import TagField
from tagging.registry import register

# Create your models here.

STATUS = {
    0: 'Draft',
    1: 'Publish',
    2: 'Delete',
}

EDITOR = [
    u'tinyMCE',
    u'MarkDown',
]



class TagField_Mine(TagField):
    def _save(self, **kwargs):
        pass


# class Editor(models.Model):
#     name = models.CharField(max_length=20, primary_key=True)
#     avaliable = models.BooleanField(default=True)
#
#     def __str__(self):
#         return self.name


class User(AbstractUser):
    name = models.CharField(max_length=20)
    editor_choice = models.CharField(max_length=20, default='tinyMCE')
    avatar_path = models.ImageField(upload_to="avatar", default="/static/image/avatar_default.jpg")

    def __str__(self):
        return self.name

class Catalogue(models.Model):   #分类，linux，python等
    name = models.CharField(max_length=20, primary_key=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    title = models.CharField(max_length=100)
    publish_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    content = models.TextField()
    catalogue = models.ForeignKey(Catalogue)
    tag = TagField_Mine()   #
    view_count = models.IntegerField(editable=False, default=0)
    status = models.SmallIntegerField(default=0, choices=STATUS.items()) #0 draft, 1 publish, 2 delete
    editor_choice = models.CharField(max_length=20)

    def __str__(self):
        return self.title

    def get_tags(self):
        return Tag.objects.get_for_object(self)    #

    def update_tags(self, tag_name):
        tag_str = "".join(tag_name)
        Tag.objects.update_tags(self, tag_str)

    def remove_tags(self):
        Tag.objects.update_tags(self, None)

    class Meta:
        ordering = ['-modify_time']


class Comment(models.Model):
    post = models.ForeignKey(Post)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)  #
    publish_Time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    content = models.TextField()
    root_id = models.IntegerField(default=0)  #0 the top comment
    parent_id = models.IntegerField(default=0) 

    def __str__(self):
        return self.content


class Carousel(models.Model):
    title = models.CharField(max_length=100)
    img = models.ImageField(upload_to="carousel")
    post = models.ForeignKey(Post)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-create_time']


class Repository(models.Model):
    title = models.CharField(max_length=100)
    publish_time = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=20)
    content = models.TextField()
    tag = models.ManyToManyField(Tag, blank=True, default="")  
    view_count = models.IntegerField(editable=False, default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-publish_time']

# class BlogPost(models.Model):
#     title = models.CharField(max_length=150)
#     body = models.TextField()
#     timestamp = models.DateTimeField()
    
#     class Meta:
#         ordering = ('-timestamp',)

# class BlogPostForm(forms.ModelForm):
#     class Meta:
#         model = BlogPost
#         exclude = ('timestamp',)

register(Post)