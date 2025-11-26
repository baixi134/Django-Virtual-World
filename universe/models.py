from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. 定义玩家 (Player)
# 我们继承了 Django 自带的用户系统，并增加了金币和等级
class Player(AbstractUser):
    coins = models.IntegerField(default=100, verbose_name="金币")
    level = models.IntegerField(default=1, verbose_name="等级")
    bio = models.TextField(blank=True, verbose_name="个人简介")

    def __str__(self):
        return self.username

# 2. 定义知识树节点 (MindNode)
# 这是一个树状结构，每个节点可以有父亲，形成 X-Mind 的结构
class MindNode(models.Model):
    title = models.CharField(max_length=200, verbose_name="观点标题")
    content = models.TextField(verbose_name="详细观点")
    
    # 谁提出的这个观点？关联到玩家
    creator = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="提出者")
    
    # 父节点：如果为空，说明它是根节点（大树的主干）
    # 如果不为空，说明它是对某个观点的延伸或评论
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children', verbose_name="父观点")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return self.title
    # 新增：交易记录表
class Transaction(models.Model):
    # 谁转出的？(related_name 是为了反向查询用的，比如查某人转出了多少次)
    sender = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='sent_transactions', verbose_name="转出者")
    # 谁收到的？
    recipient = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='received_transactions', verbose_name="接收者")
    # 转了多少？
    amount = models.IntegerField(verbose_name="金额")
    # 什么时候？
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="交易时间")

    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.amount}"