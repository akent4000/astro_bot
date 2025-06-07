from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .models import Quiz, Question
from .forms import QuizForm, QuestionFormSet, ChoiceFormSet


def quiz_editor(request, pk=None):
    if pk:
        quiz = get_object_or_404(Quiz, pk=pk)
    else:
        quiz = Quiz()

    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        q_formset = QuestionFormSet(request.POST, instance=quiz, prefix='questions')
        # validate both
        if form.is_valid() and q_formset.is_valid():
            quiz = form.save()
            q_instances = q_formset.save(commit=False)
            # handle question-level choices
            for q in q_instances:
                q.quiz = quiz
                q.save()

            # delete and save formset
            q_formset.save_m2m()

            # process each question's choices
            for q_form in q_formset:
                question = q_form.instance
                c_formset = ChoiceFormSet(
                    request.POST,
                    instance=question,
                    prefix=f'choices-{question.pk or "new"}-{q_form.prefix}'
                )
                if c_formset.is_valid():
                    choices = c_formset.save(commit=False)
                    for choice in choices:
                        choice.question = question
                        choice.save()
                    c_formset.save_m2m()
            return redirect(reverse('quiz_detail', args=[quiz.pk]))
    else:
        form = QuizForm(instance=quiz)
        q_formset = QuestionFormSet(instance=quiz, prefix='questions')

    # Prepare choice formsets placeholders
    choice_formsets = []
    for q_form in q_formset.forms:
        question = q_form.instance
        choice_formsets.append(
            ChoiceFormSet(instance=question, prefix=f'choices-{question.pk or "new"}-{q_form.prefix}')
        )

    context = {
        'form': form,
        'q_formset': q_formset,
        'choice_formsets': choice_formsets,
    }
    return render(request, 'quiz_editor.html', context)