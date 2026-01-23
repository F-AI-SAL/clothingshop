(function () {
  // Only run in inlines page
  const table = document.querySelector('.inline-group .tabular');
  if (!table) return;

  const tbody = table.querySelector('tbody');
  if (!tbody) return;

  let draggingRow = null;

  tbody.querySelectorAll('tr').forEach(tr => {
    tr.draggable = true;

    tr.addEventListener('dragstart', () => {
      draggingRow = tr;
      tr.style.opacity = "0.5";
    });

    tr.addEventListener('dragend', () => {
      tr.style.opacity = "1";
      draggingRow = null;

      // update sort_order inputs based on new order
      Array.from(tbody.querySelectorAll('tr')).forEach((row, idx) => {
        const input = row.querySelector('input[name$="sort_order"]');
        if (input) input.value = idx;
      });
    });

    tr.addEventListener('dragover', (e) => {
      e.preventDefault();
      const target = e.currentTarget;
      if (target === draggingRow) return;

      const rect = target.getBoundingClientRect();
      const next = (e.clientY - rect.top) > (rect.height / 2);

      tbody.insertBefore(draggingRow, next ? target.nextSibling : target);
    });
  });
})();
