from django.contrib import admin
from django.urls import path
from universe import views
from world_core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('register/', views.register, name='register'), # 新加的注册路径
    path('create/', views.create_node, name='create_node'), # 新加的创建节点路径
    path('transfer/', views.transfer_coins, name='transfer'), # 银行通道
    path('tip/<int:node_id>/', views.tip_node, name='tip'), # 打赏通道，注意里面的 <int:node_id>
    path('logout/', views.logout_view, name='logout'),      # 退出通道
    path('node/<int:node_id>/', views.node_detail, name='node_detail'), # 详情页
    path('node/<int:parent_id>/branch/', views.create_child_node, name='create_child'), # 分支页
    path('api/chat/', core_views.ai_chat_api, name='ai_chat_api'),
]