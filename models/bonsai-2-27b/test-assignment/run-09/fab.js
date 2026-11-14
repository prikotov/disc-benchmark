const currentYear = new Date().getFullYear();
document.getElementById('currentYear').textContent = currentYear;

const chatButton = document.getElementById('chatButton');
const popupMenu = document.getElementById('popupMenu');
const message = document.getElementById('message');

const messages = ["Остались вопросы? <br>Будем рады помочь!😌"];

let firstShow = true; // Флаг для отслеживания первого показа сообщения
let messageInterval; // Переменная для хранения интервала сообщений

// Function to show message
function showMessage() {
  // Если попап активен, не показывать сообщение
  if (popupMenu.classList.contains('active')) {
    return;
  }

  message.style.display = 'block';
  message.innerHTML = messages[Math.floor(Math.random() * messages.length)];
  message.style.opacity = '1';

  // Hide message after 20 seconds
  setTimeout(() => {
    message.style.opacity = '0';
    setTimeout(() => {
      message.style.display = 'none';
    }, 500); // Wait for fade-out to complete
  }, 20000);
}

// Function to handle message visibility and pulsation
function handleMessageVisibility() {
  if (popupMenu.classList.contains('active')) {
    message.style.display = 'none';
    chatButton.classList.remove('widget-opener__pulsation'); // Убираем пульсацию
    clearInterval(messageInterval); // Останавливаем показ сообщений
    return;
  }

  message.style.display = 'none';
  chatButton.classList.add('widget-opener__pulsation'); // Добавляем пульсацию

  // Первоначальная задержка для первого сообщения
  if (firstShow) {
    setTimeout(() => {
      showMessage();
      firstShow = false; // Устанавливаем флаг в false после первого показа
    }, 5000); // 5 секунд
  }

  // Запускаем цикл для показа сообщений только если попап скрыт
  messageInterval = setInterval(() => {
    showMessage();
  }, 30000); // Показать сообщение каждые 30 секунд
}

// Show or hide popup menu when the chat button is clicked
chatButton.addEventListener('click', () => {
  togglePopup();
});

// Function to toggle popup
function togglePopup() {
  if (popupMenu.classList.contains('active')) {
    // Hide the popup with fade-out
    popupMenu.style.opacity = '0';
    setTimeout(() => {
      popupMenu.classList.remove('active');
      handleMessageVisibility(); // Restart message visibility
    }, 500); // Wait for fade-out to complete

    // Change the icon back to comment
    chatButton.querySelector('i').classList.replace('fa-times', 'fa-comment');
  } else {
    // Change the icon to close
    chatButton.querySelector('i').classList.replace('fa-comment', 'fa-times');

    // Show the popup with fade-in
    popupMenu.classList.add('active');
    setTimeout(() => {
      popupMenu.style.opacity = '1';
    }, 10); // Slight delay for fade-in effect

    // Hide message immediately
    message.style.display = 'none';
    clearInterval(messageInterval); // Останавливаем показ сообщений
    chatButton.classList.remove('widget-opener__pulsation'); // Убираем пульсацию
  }
}

// Hide popup when clicking outside of it
document.addEventListener('click', (e) => {
  if (!popupMenu.contains(e.target) && !chatButton.contains(e.target) && popupMenu.classList.contains('active')) {
    togglePopup(); // Close the popup
  }
});

// Start showing messages on page load
handleMessageVisibility();

const scrollToTopButton = document.getElementById('scrollToTopButton');

// Показать кнопку при прокрутке страницы
window.addEventListener('scroll', () => {
  if (window.scrollY > 200) { // Показать кнопку, если прокрутили более чем на 200px
    scrollToTopButton.classList.add('show');
    scrollToTopButton.classList.remove('hide');
  } else {
    scrollToTopButton.classList.add('hide');
    scrollToTopButton.classList.remove('show');
  }
});

// Прокрутка страницы наверх при нажатии на кнопку
scrollToTopButton.addEventListener('click', () => {
  window.scrollTo({
    top: 0,
    behavior: 'smooth' // Плавная прокрутка наверх
  });
});

const experienceElement = document.getElementById("experience");

if (experienceElement) {
  const startYear = 2009;
  const yearsOfExperience = new Date().getFullYear() - startYear;

  // Если у элемента есть оба класса — добавляем "+"
  if (
    experienceElement.classList.contains("stats-achievements__num") &&
    experienceElement.classList.contains("t-accent-additional")
  ) {
    experienceElement.textContent = yearsOfExperience + "+";
  } else {
    experienceElement.textContent = yearsOfExperience;
  }
}
