import uuid

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Code(models.Model):
    code = models.TextField()


class AI_Code(models.Model):
    Input_message = models.TextField()


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    structure = models.JSONField()  # This field will now store a list of module titles
    objective = models.TextField()
    num_lessons = models.IntegerField(default=0)  # New field for number of lessons
    num_tasks = models.IntegerField(default=0)  # New field for number of lessons

    def __str__(self):
        return self.title

class Module(models.Model):
    number = models.IntegerField()
    title = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return f"Module {self.number}: {self.title}"


class Lesson(models.Model):
    number = models.IntegerField()
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=2000)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)

    def __str__(self):
        return f"Lesson {self.number}: {self.title}"


class Task(models.Model):
    task_name = models.CharField(max_length=100)
    description = models.TextField()
    correct_code = models.TextField()
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)

    def __str__(self):
        return self.task_name


class Task_thread(models.Model):
    thread_id = models.CharField(max_length=200)
    assistant_id = models.CharField(max_length=200)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    tasks_solved = models.IntegerField(default=0)
    runs = models.IntegerField(default=0)
    prompts = models.JSONField(default=dict)  # Thisfield will now store a list
    learning_thread = models.JSONField(default=list)  # This field will now store a list
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class TextContent(models.Model):
    content = models.TextField()


class CodeContent(models.Model):
    code = models.TextField()

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class FileStructure(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10)  # 'file' or 'folder'
    content = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} - {self.user.username}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    deployed_apps = models.JSONField(default=dict)

    def __str__(self):
        return self.user.username

    @receiver(post_save, sender=User)
    def create_or_update_user_profile(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.create(user=instance)
        else:
            instance.userprofile.save()