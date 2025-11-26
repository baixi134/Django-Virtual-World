from django.contrib import admin
from .models import Player, MindNode

# 把我们的模型注册到后台
admin.site.register(Player)
admin.site.register(MindNode)