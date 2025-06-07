from django import forms
from django.forms import inlineformset_factory
from tgbot.models import SSHKey, TelegramUser, Quiz, Question, Choice

class SSHKeyAdminForm(forms.ModelForm):
    # Дополнительные поля используются только при создании ключа
    passphrase = forms.CharField(
        required=False, label="Пароль", widget=forms.PasswordInput(render_value=True)
    )
    key_type = forms.ChoiceField(
        choices=[("rsa", "RSA"), ("ed25519", "Ed25519")],
        initial="rsa",
        label="Тип ключа"
    )
    bits = forms.IntegerField(initial=2048, label="Размер ключа (для RSA)", required=False)

    class Meta:
        model = SSHKey
        # Используем key_name как основное поле, оно также служит комментарием
        fields = ("key_name", "passphrase", "key_type", "bits")

# Форма для редактирования (change view), которая показывает только поле key_name
class SSHKeyChangeForm(forms.ModelForm):
    class Meta:
        model = SSHKey
        fields = ("key_name",)

class SendMessageForm(forms.Form):
    message = forms.CharField(
        label="Текст сообщения",
        widget=forms.Textarea(attrs={"rows": 4, "cols": 40}),
        required=True
    )
    sender = forms.ModelChoiceField(
        label="Отправить от имени",
        queryset=TelegramUser.objects.filter(is_admin=True),
        widget=forms.Select,
        required=True
    )

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'topic', 'level']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'topic': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'explanation', 'order']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

# Inline formsets
QuestionFormSet = inlineformset_factory(
    Quiz, Question,
    form=QuestionForm,
    extra=1,
    can_delete=True
)
ChoiceFormSet = inlineformset_factory(
    Question, Choice,
    form=ChoiceForm,
    extra=2,
    can_delete=True
)