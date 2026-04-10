import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import PlayPage from "./pages/PlayPage";
import GalleryPage from "./pages/GalleryPage";
import PrivacyPage from "./pages/PrivacyPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/play/:id" element={<PlayPage />} />
      <Route path="/gallery" element={<GalleryPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
    </Routes>
  );
}
