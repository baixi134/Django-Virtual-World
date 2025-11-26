from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Player

# 我们创建一个专门针对 Player (玩家) 的注册表单
class PlayerRegisterForm(UserCreationForm):
    class Meta:
        model = Player
        # 注册时只需要填用户名，密码是 UserCreationForm 自带处理的
        fields = ['username', 'email']
from .models import MindNode  # 别忘了引入 MindNode

# 新增：发布观点的表单
class NodeForm(forms.ModelForm):
    class Meta:
        model = MindNode
        fields = ['title', 'content'] # 用户只需要填标题和内容
        # 我们可以给输入框加点样式，让它好看点（可选）
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '请输入核心观点...', 'style': 'width: 100%; padding: 10px;'}),
            'content': forms.Textarea(attrs={'placeholder': '详细阐述你的想法...', 'style': 'width: 100%; padding: 10px; height: 100px;'}),
        }
        # 新增：转账表单
class TransferForm(forms.Form):
    recipient_username = forms.CharField(label="对方用户名", max_length=150, widget=forms.TextInput(attrs={'placeholder': '输入你要转账的用户...'}))
    amount = forms.IntegerField(label="转账金额", min_value=1, widget=forms.NumberInput(attrs={'placeholder': '输入金额...'}))