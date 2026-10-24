from django.urls import path

from apps.reviews.views import MyReviewView, ReviewListCreateView

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="reviews"),
    path("mine/", MyReviewView.as_view(), name="my-review"),
]
