# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from datetime import datetime
from forms import SignUpForm, LoginForm, PostForm, LikeForm, CommentForm
from django.contrib.auth.hashers import make_password, check_password
from models import UserModel, SessionToken, PostModel, LikeModel, CommentModel
from instaclone.settings import BASE_DIR
from imgurpython import ImgurClient
from clarifai.rest import ClarifaiApp

# Create your views here.


#view for signup

def signup_view(request):
    today = datetime.now()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = UserModel(name=name, password=make_password(password), email=email, username=username)
            user.save()
            return render(request, 'success.html')
        else:
            form = SignUpForm()
    elif request.method == "GET":
        form = SignUpForm()

    return render(request, 'index.html', {'today': today}, {'form': form})

#view for login
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

#view for feed page
def feed_view(request):
    return render(request, 'feed.html')


# For validating the session
def check_validation(request):
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            return session.user
    else:
        return None

#view to upload a image in post
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
                client = ImgurClient('13b7a6dc4e65cab', 'fdb7b0994e9cdca1303402e208c01eafafac0122')
                post.image_url = client.upload_from_path(path, anon=True)['link']
                post.save()
                clarifai_data = []
                app = ClarifaiApp(api_key='fcfdca12d67a4af7b657c4117ea90128')  # Covers all scopes
                model = app.models.get("general-v1.3")
                result = model.predict_by_url(url=post.image_url)
                for x in range(0, len(result['outputs'][0]['data']['concepts'])):
                    model = result['outputs'][0]['data']['concepts'][x]['name']
                    clarifai_data.append(model)
                for z in range(0, len(clarifai_data)):
                    print clarifai_data[z]
                return redirect('/feed/')


        else:
            form = PostForm()
        return render(request, 'post.html', {'form': form})

    else:
        return redirect('/login/')

#like function in feed view
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

#view for like
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

#view for comment
def comment_view(request):
  user = check_validation(request)
  if user and request.method == 'POST':
    form = CommentForm(request.POST)
    if form.is_valid():
      post_id = form.cleaned_data.get('post').id
      comment_text = form.cleaned_data.get('comment_text')
      comment = CommentModel.objects.create(user=user, post_id=post_id, comment_text=comment_text)
      comment.save()
      return redirect('/feed/')
    else:
      return redirect('/feed/')
  else:
    return redirect('/login')



