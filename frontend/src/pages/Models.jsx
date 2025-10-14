import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

export default function Models({ token }) {
  const [models, setModels] = useState([]);

  const fetchModels = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:5001/models/models", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setModels(res.data || []);
    } catch (err) {
      console.error("Failed to fetch models:", err);
    }
  };

  useEffect(() => {
    fetchModels();
    const interval = setInterval(fetchModels, 5000); // polling la 5 sec
    return () => clearInterval(interval);
  }, [token]);

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Models</h2>
        <Link
          to="/upload/model"
          className="bg-green-600 text-white px-3 py-1 rounded"
        >
          Upload Model
        </Link>
      </div>
      <table className="min-w-full border">
        <thead>
          <tr className="bg-gray-200">
            <th className="p-2 border">Name</th>
            <th className="p-2 border">Description</th>
            <th className="p-2 border">Status</th>
            <th className="p-2 border">On-chain TX</th>
            <th className="p-2 border">Model PDA</th>
            <th className="p-2 border">Error</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.id} className="border-t">
              <td className="p-2 border">{m.name}</td>
              <td className="p-2 border">{m.description}</td>
              <td className="p-2 border">{m.status || "pending"}</td>
              <td className="p-2 border">{m.onchain_tx || "-"}</td>
              <td className="p-2 border">{m.model_pda || "-"}</td>
              <td className="p-2 border">{m.last_error || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
