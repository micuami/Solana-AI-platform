import React from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Models({ token }) {
  const [models, setModels] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:5001/models/models", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.json())
      .then(data => setModels(data || []))
      .catch(err => console.error(err));
  }, [token]);

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Models</h2>
        <Link to="/upload/model" className="bg-green-600 text-white px-3 py-1 rounded">Upload Model</Link>
      </div>
      <ul className="space-y-2">
        {models.map(m => (
          <li key={m.id} className="border p-2 rounded">{m.name} - {m.description}</li>
        ))}
      </ul>
    </div>
  );
}
