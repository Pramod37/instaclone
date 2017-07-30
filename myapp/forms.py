from django import forms
from models import UserModel, PostModel, LikeModel, CommentModel


# signup form to show signup view
class SignUpForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ['email', 'username', 'name', 'password']


# login form to show login view
class LoginForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ['username', 'password']


# post form to show post view
class PostForm(forms.ModelForm):
    class Meta:
        model = PostModel
        fields = ['image', 'caption']


# like form to show like view
class LikeForm(forms.ModelForm):
    class Meta:
        model = LikeModel
        fields = ['post']


# comment form to show commnt view
class CommentForm(forms.ModelForm):
    class Meta:
        model = CommentModel
        fields = ['comment_text', 'post']


# UpVote form
class UpVoteForm(forms.Form):
    id = forms.IntegerField
