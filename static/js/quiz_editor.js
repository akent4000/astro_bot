$(function() {
  var $questions = $('#questions-container');
  var totalForms = $('#id_questions-TOTAL_FORMS');

  $('#add-question').on('click', function() {
    var formIdx = parseInt(totalForms.val());
    var tmpl = $questions.find('.question-block:first').clone();
    tmpl.attr('data-index', formIdx);
    tmpl.find(':input').each(function() {
      var name = $(this).attr('name').replace(/questions-\d+-/, 'questions-' + formIdx + '-');
      var id = 'id_' + name;
      $(this).attr({'name': name, 'id': id}).val('').prop('checked', false);
    });
    tmpl.appendTo($questions);
    totalForms.val(formIdx + 1);
  });

  $questions.on('click', '.remove-question', function() {
    var $block = $(this).closest('.question-block');
    $block.remove();
    // TODO: renumber forms and TOTAL_FORMS
  });
});