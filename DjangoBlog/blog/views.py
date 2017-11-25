# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import datetime
import json
import re
import os
import uuid
from django.views.decorators.csrf import csrf_exempt
from django.template.response import TemplateResponse
from django.views.generic import View, ListView, CreateView, UpdateView, DetailView
from django.http import HttpResponse, HttpResponseRedirect
from .models import Post, Carousel, Comment, Repository, Catalogue, User
from blog.pagination import paginator_tool
from DjangoBlog.settings import PERNUM
from django.contrib.auth import get_user_model
from collections import OrderedDict
# from django.template.context import Context

# Create your views here.
class BaseMixin(object):
    def get_context_data(self, **kwargs):
        context = super(BaseMixin, self).get_context_data(**kwargs)
        try:
            context['hot_artical_list'] = Post.objects.filter(status=1).order_by('-view_count')[0:10]
            context['man_list'] = get_user_model().objects.raw('select *, COUNT(post.id) as counts from blog_user as user LEFT JOIN blog_post post ON post.status=1 and post.author_id=user.id GROUP BY user.id')
        except Exception as e:
            print e
        return context

class IndexView(BaseMixin, ListView):
    template_name = 'blog/index.html'
    context_object_name = 'post_list'
    
    queryset = Post.objects.filter(status=1)

    def get_context_data(self, **kwargs):
        page = self.kwargs.get('page') or self.request.GET.get('page') or 1
        objects, page_range = paginator_tool(pages=page, queryset=self.queryset, display_amount=PERNUM)
        context = super(IndexView, self).get_context_data(**kwargs)
        # print Context
        # print Context['carousel_page_list']
        context['carousel_page_list'] = Carousel.objects.all()
        context['page_range'] = page_range
        context['objects'] = objects

        return context

# def foo(request):
#     # post = BlogPost(title='mocktitle', body='mockbody', timestamp=datetime.now())
#     # return render_to_response('archive.html', {'posts': [post]})
#     # context['body'] = r'hello world'
#     return render(request, 'blog/index.html', {'body':r'hello world'})

class PostView(BaseMixin, DetailView):
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    queryset = Post.objects.filter(status=1)

    def get(self, request, *args, **kwargs):
        pkey = self.kwargs.get('pk')
        posts = self.queryset.get(pk=pkey)
        posts.view_count+=1
        posts.save()
        return super(PostView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PostView, self).get_context_data(**kwargs)
        pkey = self.kwargs.get('pk')
        comment_queryset = self.queryset.get(pk=pkey).comment_set.all().order_by('publish_Time')  ##
        comment_dict = self.handle_comment(comment_queryset)
        context['comment_list'] = comment_dict
        return context

    def handle_comment(self, queryset):
        comment_dict = OrderedDict()
        root_list = []
        child_list = []
        every_child_list = []

        for comment in queryset:
            if comment.root_id == 0:
                root_list.append(comment)
            else:
                child_list.append(comment)
        
        for root_comment in root_list:
            for child_comment in child_list:
                if child_comment.root_id == root_comment.id:
                    every_child_list.append(child_comment)
            comment_dict[root_comment] = every_child_list
            every_child_list = []
        return comment_dict

class CommentView(View):
    def post(self, request, *args, **kwargs):
        user = self.request.user  #
        comment = self.request.POST.get("comment", "")
        root_id = self.request.POST.get("root_id", "")
        parent_id = self.request.POST.get("parent_id", "")

        if not user.is_authenticated():
            return HttpResponse(u'', status=403)
        if not comment:
            return HttpResponse(u'', status=403)
        if len(comment)>200:
            return HttpResponse(u'', status=403)

        if request.META.has_key("HTTP_X_FORWARDED_FOR"):
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']

        comment = self.handle_at_str(comment)

        if root_id ==0:
            comment = self.handle_emoji_str(comment)

        pkey = self.kwargs.get('pk', "")
        post_foreignkey = Post.object.get(pk=pkey)

        comment = Comment.object.create(
            post = post_foreignkey,
            author = user,
            conent = comment,
            id_address = ip,
            root_id = root_id,
            parent_id = parent_id,
        )

        result_dict = {
            'post_id':post_foreignkey.id,
            'csrf_token':request.COOKIES['csrftokern'],
            'user_id': user.id,
            'author_id': comment.author.id,
            'comment_id': comment.id,
            'comment_author': comment.author.name,
            'comment_publish_time': comment.publish_time,
            'comment_content': comment.conent,
        }
        
        return HttpResponse(json.dumps(result_dict))

    def handle_at_str(self, str):
        pattern = re.compile('@\S+')
        result = pattern.findall(str)
        for string in result:
            handler_str = '<a>' + string + '</a>'
            str = re.sub(string, handler_str, str)
        return str

    def handle_emoji_str(self, str):
        keys = ':(add1|-1|airplane|alarm_clock|alien|angel|angry|anguished|art|astonished|basketball|beers|bicyclist|birthday|blush|broken_heart|cat|chicken|clap|confounded|confused|cow|cry|disappointed|dizzy_face|dog|expressionless|fearful|flushed|frowning|full_moon_with_face|ghost|grimacing|grin|grinning|heart_eyes|high_brightness|hushed|innocent|joy|kissing_heart|laughing|mask|neutral_face|new_moon_with_face|pencil2|persevere|person_frowning|person_with_blond_hair|relaxed|relieved|satisfied|scream|sleeping|smile|smirk|sob|stuck_out_tongue_winking_eye|sunglasses|sweat|tired_face|triumph|tulip|u7981|unamused|unlock|v|weary|wink|worried|yum|zzz)'
        pattern = re.compile(keys)
        result = pattern.findall(str)
        for string in result:
            key = string
            url = '/static/jquery-emojiarea/packs/basic/emojis'
            extension = '.png'
            src = url + '/' + key + extension
            handler_str = '<img class="emoji" width="20" height="20" align="absmiddle" src="'+src+'"/>'
            str = re.sub(':'+string+':', handler_str, str)
        return str

class CommentDeleteView(View):
    def post(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated():
            return HttpResponse(u'', status=403)
        pkey = self.kwargs.get('pk', "")
        comment = Comment.objects.filter(author_id=user.id).get(pk=pkey)

        if comment.root_id == 0:
            children_comment_set = Comment.objects.filter(root_id=comment.id)
            children_comment_set.delete()

        result = {'comment_id': comment.id}
        comment.delete()

        return HttpResponse(json.dumps(result))

class TagListView(BaseMixin, ListView):
    template_name = 'blog/index.html'
    context_object_name = 'post_list'

    def get_queryset(self):
        slug_key = self.kwargs.get("slug")
        post_list = TaggedItem.objects.get_by_model(Post, slug_key) ####
        return post_list

    def get_context_data(self, **kwargs):
        page = self.kwargs.get('page') or self.request.GET.get('page') or 1
        objects, page_range = paginator_tool(pages=page, queryset=self.get_queryset(), display_amount=PERNUM)
        context = super(TagListView, self).get_context_data(**kwargs)
        context['carousel_page_list'] = Carousel.objects.all()
        context['page_range'] = page_range
        context['objects'] = objects
        return context

class CategoryListView(BaseMixin, ListView):
    template_name = 'blog/index.html'
    context_object_name = 'post_list'

    def get_queryset(self):
        slug_key = self.kwargs.get('slug')
        catalogue_key = Catalogue.objects.get(pk=slug_key)
        post_list = Post.objects.filter(catalogue_id=catalogue_key)
        return post_list

    def get_context_data(self, **kwargs):
        page = self.kwargs.get('page') or self.request.GET.get('page') or 1
        objects, page_range = paginator_tool(pages=page, queryset=self.get_queryset(), display_amount=PERNUM)
        context = super(CategoryListView, self).get_context_data(**kwargs)
        context['carousel_page_list'] = Carousel.objects.all()
        context['page_range'] = page_range
        context['objects'] = objects
        return context

class AuthorPostListView(BaseMixin, ListView):
    template_name = 'blog/index.html'
    context_object_name = 'post_list'

    def get_queryset(self):
        pkey = self.kwargs.get('pk')
        user = User.objects.get(pk=pkey)
        post_list = Post.objects.filter(author_id=user).filter(status=1)
        print post_list
        return post_list
    
    def get_context_data(self, **kwargs):
        page = self.kwargs.get('page') or self.request.GET.get('page') or 1
        objects, page_range = paginator_tool(pages=page, queryset=self.get_queryset(), display_amount=PERNUM)
        # user paginator_tool to get page list and item_range for "pages"
        context = super(AuthorPostListView, self).get_context_data(**kwargs)
        context['carousel_page_list'] = Carousel.objects.all()
        context['page_range'] = page_range
        context['objects'] = objects
        return context
