'use client'

import { useState } from "react";
import axios from "axios"

export default function Home() {

  const [fileWorkbank, setFileWorkbank] = useState<File | null>(null)
  const [fileBank, setFileBank] = useState<File | null>(null)
  const [bank, setBank] = useState<string>()
  const [message, setMessage] = useState<string>()
  const [loading, setLoading] = useState<boolean>(false)

  async function sendToQueue(e) {
    e.preventDefault()

    setLoading(true)

    const url = process.env.API_URL_QUEUE
    const form = new FormData()

    form.append('fileWork', fileWorkbank!)
    form.append('fileBank', fileBank!)
    form.append("bank", bank!)

    try {
      const response = await axios.post(`${url}/pricing`, form)

      if (response.status >= 200 && response.status < 300) {
        setMessage(response.data);
      }

      console.log("Finalizado o input")

    } catch(e) {
      console.error("Erro na requisição:", e);
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="flex flex-col justify-center items-center h-screen w-screen bg-gray-50 p-4">
      <div className="w-full max-w-md bg-white p-8 rounded-xl shadow-md border border-gray-100">

        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">
          Upload de Relatórios
        </h1>

        <div className="space-y-6">
          {/* Campo Workbank */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">Arquivo Workbank</label>
            <input
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-md cursor-pointer focus:outline-none"
              type="file"
              onChange={(e) => {
                const selectedFile = e.target.files?.[0];
                if (selectedFile) setFileWorkbank(selectedFile);
              }}
            />
          </div>

          {/* Campo Bank */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">Arquivo Bank</label>
            <input
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-md cursor-pointer focus:outline-none"
              type="file"
              onChange={(e) => {
                const selectedFile = e.target.files?.[0];
                if (selectedFile) setFileBank(selectedFile);
              }}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">Arquivo Bank</label>
            <select
              className="w-full py-2 px-1 text-sm text-gray-500  border border-gray-300 rounded-md cursor-pointer"
              onChange={(e) => {
                const selectedBank = e.target.value;
                setBank(selectedBank);
              }}
            >
              <option className="hidden" value="">Selecione um banco</option>
              <option value="Capital Consig">Capital Consig</option>
            </select>
          </div>

          {/* Botão de Envio */}
          <button
            type="button"
            disabled={loading}
            onClick={(e) => sendToQueue(e)}
            className={`w-full py-3 px-4 rounded-md font-semibold text-white transition-colors
              ${loading
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 active:bg-blue-800"}`}
          >
            {loading ? "Processando..." : "Enviar para Fila"}
          </button>

          {/* Mensagem de Sucesso */}
          {message && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-green-700 text-center font-medium">✅ Arquivos enviados com sucesso!</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
