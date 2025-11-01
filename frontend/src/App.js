import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "@/pages/Dashboard";
import AppDetails from "@/pages/AppDetails";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/apps/:id" element={<AppDetails />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
