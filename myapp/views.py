# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from datetime import timedelta
from django.utils import timezone
from forms import SignUpForm, LoginForm, PostForm, LikeForm, CommentForm, Upvoteform
from django.contrib.auth.hashers import make_password, check_password
from models import UserModel, SessionToken, PostModel, LikeModel, CommentModel, CategoryModel
from instaclone.settings import BASE_DIR
from imgurpython import ImgurClient
from myapp.keys import YOUR_CLIENT_ID,YOUR_CLIENT_SECRET,SENDGRID_API_KEY
from clarifai.rest import ClarifaiApp
import json
import sendgrid
import os
from sendgrid.helpers.mail import *

# signup view has the functionality of signing up for a new user
# it also sends a welcome email via sendgrid

def signup_view(request):

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            if (len(form.cleaned_data['username']) < 5 or set('[~!#$%^&*()_+{}":;\']+$ " "').intersection(form.cleaned_data['username'])):
                return render(request, 'invalid.html')
            else:
                if (len(form.cleaned_data["password"]) > 5):
                    username = form.cleaned_data['username']
                    name = form.cleaned_data['name']
                    email = form.cleaned_data['email']
                    password = form.cleaned_data['password']
                    user = UserModel(name=name, password=make_password(password), email=email, username=username)
                    user.save()
                    sg = sendgrid.SendGridAPIClient(apikey=(SENDGRID_API_KEY))
                    from_email = Email("prmdmriu@gmail.com")
                    to_email = Email(form.cleaned_data['email'])
                    subject = "Welcome to Smartblog"
                    content = Content("text/plain","Team Instaclone welcomes you!\n We hope you enjoy sharing your precious moments blogging them /n")
                    mail = Mail(from_email, subject, to_email, content)
                    response = sg.client.mail.send.post(request_body=mail.get())
                    print(response.status_code)
                    print(response.body)
                    print(response.headers)
                    return render(request, 'success.html')
                else:
                    form = SignUpForm()
    elif request.method == "GET":
        form = SignUpForm()

    return render(request, 'index.html', {'form': form})

# login view lets the old user login using username and password
# It creates a session token and incorrect message
def login_view(request):
    response_data = {}
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = UserModel.objects.filter(username=username).first()
            if user:

                # Check for the password
                if check_password(password, user.password):
                    print 'User is valid'
                    token = SessionToken(user=user)
                    token.create_token()
                    token.save()
                    response = redirect('feed/')
                    response.set_cookie(key='session_token', value=token.session_token)
                    return response
                else:
                    response_data['message'] = 'Incorrect Password! Please try again!'
    elif request.method == "GET":
        form = LoginForm()
    response_data['form'] = form

    return render(request, 'login.html' ,response_data)


# feed view show post,psted by logged in user




# For validating the session

def check_validation(request):
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            time_to_live = session.created_on + timedelta(days=1)
        if time_to_live > timezone.now():
            return session.user

    else:
        return None


# post view function to upload a image for feed page nd use of clarifai for category

def post_view(request):
    user = check_validation(request)
    if user:
        if request.method == 'GET':
            form = PostForm()
            return render(request, 'post.html', {'form': form})
        elif request.method == 'POST':
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data.get('image')
                caption = form.cleaned_data.get('caption')
                post = PostModel(user=user, image=image, caption=caption)
                post.save()
                path = str(BASE_DIR +"/"+ post.image.url)
                client = ImgurClient(YOUR_CLIENT_ID, YOUR_CLIENT_SECRET)
                post.image_url = client.upload_from_path(path, anon=True)['link']
                post.save()
                clarifai_data = []
                app = ClarifaiApp(api_key='fcfdca12d67a4af7b657c4117ea90128')  # Covers all scopes
                model = app.models.get("general-v1.3")
                response = model.predict_by_url(url=post.image_url)

                file_name = 'output' + '.json'

                for json_dict in response:
                    for key, value in response.iteritems():
                        print("key: {} | value: {}".format(key, value))
                post.save()
                return redirect('/feed/')
        else:
            form = PostForm()
        return render(request, 'post.html', {'form': form})
    else:
        return redirect('/login/')


# feed view show post,posted by logged in user

def feed_view(request):
    user = check_validation(request)
    if user:

        posts = PostModel.objects.all().order_by('-created_on')
        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True
            return render(request, 'feed.html', {'posts': posts})
    else:
        return redirect('/login/')


# like view function for like a post by loggedin user

def like_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = LikeForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            existing_like = LikeModel.objects.filter(post_id=post_id, user=user).first()
            if not existing_like:
                LikeModel.objects.create(post_id=post_id, user=user)
            else:
                existing_like.delete()
            return redirect('/feed/')
    else:
        return redirect('/login/')


# comment view function for comment on a post
# send an alert email when comment by an user on any user post by sendgrid
def comment_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            comment_text = form.cleaned_data.get('comment_text')
            comment = CommentModel.objects.create(user=user, post_id=post_id, comment_text=comment_text)
            comment.save()
            sg = sendgrid.SendGridAPIClient(apikey=(SENDGRID_API_KEY))
            from_email = Email("prmdmriu@gmail.com")
            to_email = Email(form.cleaned_data['email'])
            subject = "Welcome to Instaclone"
            content = Content("text/plain","Team Instaclone welcomes you!\n We hope you enjoy sharing your precious moments blogging them /n")
            mail = Mail(from_email, subject, to_email, content)
            response = sg.client.mail.send.post(request_body=mail.get())
            print(response.status_code)
            print(response.body)
            print(response.headers)
            return redirect('/feed/')
        else:
            return redirect('/feed/')
    else:
        return redirect('/login')

# Function to view to see post from a particular user
def self_view(request):
    user = check_validation(request)
    if user:
        posts = PostModel.objects.filter(user=user).order_by('-created_on')
        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True
            return render(request, 'feed.html', {'posts': posts, 'user': user})
        else:
            return redirect('/login/')




# logout function view for logout from feed page

def logout_view(request):
    user = check_validation(request)
    if user:
        token=SessionToken.objects.get(session_token=request.COOKIES.get("session_token"))
        token.is_valid=False
        token.save()
    return redirect('/login/')


# UpVote view function to upvote any comment
def upvote_view(request):
    user = check_validation(request)
    comment = None

    print ("upvote view")
    if user and request.method == 'POST':

        form = Upvoteform(request.POST)
        if form.is_valid():

            comment_id = int(form.cleaned_data.get('id'))

            comment = CommentModel.objects.filter(id=comment_id).first()
            print ("upvoted not yet")

            if comment is not None:
                # print ' unliking post'
                print ("upvoted")
                comment.upvote_num+=1
                comment.save()
                print (comment.upvote_num)
            else:
                print ('stupid mistake')
                #liked_msg = 'Unliked!'

        return redirect('/feed/')
    else:
        return redirect('/feed/')

# this view show the automatic categories
def add_category(post):
    app = ClarifaiApp(api_key='fcfdca12d67a4af7b657c4117ea90128')
    model = app.models.get("general-v1.3")
    response = model.predict_by_url(url=post.image_url)
    if response["status"]["code"]==10000:
        if response["outputs"]:
            if response["output"][0]["data"]:
                if response["output"][0]["data"]["concepts"]:
                    for index in range (0,len(response["outputs"][0]["data"]["concepts"])):
                        category=CategoryModel(post=post,category_text=response['outputs'][0]['data']['concepts'][index]['name'])
                        category.save()
                else:
                    print 'no concepts error'
            else:
                print 'no data list error'
        else:
            print 'no outtput list error'
    else:
        print 'response code error'


