function filterTools() {
      const input = document.getElementById('search').value.toLowerCase();
      const cards = document.querySelectorAll('.tool-card');
      cards.forEach(card => {
        const keywords = card.dataset.keywords.toLowerCase();
        const title = card.querySelector('h3').innerText.toLowerCase();
        if (keywords.includes(input) || title.includes(input)) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    }