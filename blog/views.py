from django.shortcuts import render
from django.db.models import Q
from django.views.generic import TemplateView, ListView

# Create your views here.
from django.shortcuts import render
from blog.models_old import Post, Comment
from blog.models import Embeddings

from blog.embedding import get_embeddings
from pgvector.django import L2Distance

def index(request):
    if(request.method == 'POST'):
        text = request.POST.get('input_text')
        # create embedding of text 
        embedding = get_embeddings(text)
        top3 = list(Embeddings.objects.order_by(
            L2Distance('embedding', embedding)
        ))[:3]
        
        context = {
            'search_text': text, 
            'results': top3
        }
        return render(request, 'blog/results.html', context)
    
    embeddings = Embeddings.objects.all() 
    print("emeddings: ", embeddings)
    context = {'embeddings': embeddings}
    return render(request, 'blog/index.html', context)

def blog_index(request):
    posts = Post.objects.all().order_by("-created_on")
    context = {
        "posts": posts,
    }
    return render(request, "blog/index.html", context)

def blog_category(request, category):
    posts = Post.objects.filter(
        categories__name__contains=category
    ).order_by("-created_on")
    context = {
        "category": category,
        "posts": posts,
    }
    return render(request, "blog/category.html", context)

def blog_detail(request, pk):
    post = Post.objects.get(pk=pk)
    comments = Comment.objects.filter(post=post)
    context = {
        "post": post,
        "comments": comments,
    }

    return render(request, "blog/detail.html", context)

class SearchResultsView(ListView):
    model = Post
    template_name = 'search_results.html'

    def get_queryset(self):
       query = self.request.GET.get("q")
       return Post.objects.filter(
           Q(title__icontains=query) | Q(body__icontains=query)
       )
    