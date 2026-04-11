import { Link } from "react-router-dom";

export default function PrivacyPage() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", lineHeight: 1.7 }}>
      <h1>Приватность 🔒</h1>
      <p style={{ marginTop: "1rem", color: "var(--color-text-muted)" }}>
        Играйка создан для детей и их семей. Мы серьёзно относимся
        к приватности и всё делаем просто.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Что мы сохраняем</h2>
      <ul style={{ marginTop: "0.5rem" }}>
        <li><strong>Идеи игр</strong> &mdash; текст, который ты пишешь.</li>
        <li><strong>Созданные игры</strong> &mdash; HTML-игры, которые делает ИИ.</li>
      </ul>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Что мы НЕ собираем</h2>
      <ul style={{ marginTop: "0.5rem" }}>
        <li>Никаких имён, email или возраста</li>
        <li>Никаких паролей или аккаунтов</li>
        <li>Никакой личной информации вообще</li>
      </ul>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Анонимные сессии</h2>
      <p style={{ marginTop: "0.5rem" }}>
        Когда ты заходишь на Играйка, мы создаём случайный ID в cookie,
        который живёт 24 часа. Он нужен только чтобы показывать тебе
        твои игры и защищать от злоупотреблений. По нему нельзя тебя узнать.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Хранение данных</h2>
      <p style={{ marginTop: "0.5rem" }}>
        Все игры и идеи <strong>автоматически удаляются через 30 дней</strong>.
        Ничего не хранится вечно.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Сторонние сервисы</h2>
      <p style={{ marginTop: "0.5rem" }}>
        Когда ты создаёшь игру, твоя идея отправляется в ИИ-сервис
        (OpenRouter) для генерации. Мы не отправляем туда никакой личной
        информации.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Без слежки</h2>
      <ul style={{ marginTop: "0.5rem" }}>
        <li>Нет аналитики или трекинга</li>
        <li>Нет рекламы</li>
        <li>Нет сторонних cookie</li>
        <li>Данные никому не передаются</li>
      </ul>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Вопросы?</h2>
      <p style={{ marginTop: "0.5rem" }}>
        Если есть вопросы — попроси родителя или учителя связаться с нами!
      </p>

      <Link to="/" style={{ marginTop: "2rem", display: "inline-block", color: "var(--color-primary)" }}>
        На главную 🏠</Link>
    </div>
  );
}
