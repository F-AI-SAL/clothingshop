document.addEventListener('DOMContentLoaded', function () {
  const inlines = document.querySelectorAll('.inline-group');
  inlines.forEach((group) => {
    const tbody = group.querySelector('tbody');
    if (!tbody || !window.Sortable) return;
    Sortable.create(tbody, {
      handle: 'tr',
      animation: 150,
      onEnd: function () {
        const rows = tbody.querySelectorAll('tr.form-row');
        rows.forEach((row, index) => {
          const input = row.querySelector('input[id$="sort_order"]');
          if (input) input.value = index;
        });
      }
    });
  });
});
