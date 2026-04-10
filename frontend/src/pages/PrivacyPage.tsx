import { Link } from "react-router-dom";

export default function PrivacyPage() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", lineHeight: 1.7 }}>
      <h1>Privacy Policy</h1>
      <p style={{ marginTop: "1rem", color: "var(--color-text-muted)" }}>
        GameSpark is built for kids and families. We take your privacy seriously
        and keep things simple.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>What We Collect</h2>
      <ul style={{ marginTop: "0.5rem" }}>
        <li>
          <strong>Game ideas</strong> &mdash; the prompts you type to describe your game.
        </li>
        <li>
          <strong>Generated games</strong> &mdash; the HTML games our AI creates for you.
        </li>
      </ul>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>What We Do NOT Collect</h2>
      <ul style={{ marginTop: "0.5rem" }}>
        <li>No names, emails, or ages</li>
        <li>No passwords or accounts</li>
        <li>No personal information of any kind</li>
      </ul>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Anonymous Sessions</h2>
      <p style={{ marginTop: "0.5rem" }}>
        When you visit GameSpark, we create a random session ID stored in a cookie
        that expires after 24 hours. This ID is used only to show you your own
        games and to prevent abuse. It cannot be used to identify you.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Data Retention</h2>
      <p style={{ marginTop: "0.5rem" }}>
        All games and prompts are <strong>automatically deleted after 30 days</strong>.
        Nothing is kept forever.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Third-Party Services</h2>
      <p style={{ marginTop: "0.5rem" }}>
        When you create a game, your game idea (prompt) is sent to an AI service
        (OpenRouter) to generate the game. OpenRouter processes the prompt and
        returns the result. We do not send any personal information to this service.
      </p>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>No Tracking</h2>
      <ul style={{ marginTop: "0.5rem" }}>
        <li>No analytics or tracking scripts</li>
        <li>No advertising</li>
        <li>No third-party cookies</li>
        <li>No data shared with anyone else</li>
      </ul>

      <h2 style={{ marginTop: "1.5rem", fontSize: "1.2rem" }}>Questions?</h2>
      <p style={{ marginTop: "0.5rem" }}>
        If you have any questions about how GameSpark handles your data, please
        ask a parent or teacher to get in touch with us.
      </p>

      <Link to="/" style={{ marginTop: "2rem", display: "inline-block", color: "var(--color-primary)" }}>
        Back to Home
      </Link>
    </div>
  );
}
