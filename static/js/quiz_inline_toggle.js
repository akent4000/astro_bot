(function($) {
  $(function() {
    // для каждого вопроса
    $('.inline-related').each(function() {
      var $inline = $(this);
      // само поле variants (nested inline)
      var $variants = $inline.find('.inline-group');
      // по клику на строку вопроса — показывать/скрывать варианты
      $inline.find('tr > th > a').on('click', function(e) {
        // ссылка show_change_link, пусть ведёт как раньше, а toggle variants по клику на текст
        e.preventDefault();
        $variants.slideToggle();
      });
    });
  });
})(django.jQuery);
