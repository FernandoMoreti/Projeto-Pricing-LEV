'use client'

import { useState } from "react";
import axios from "axios";
import {
  Upload,
  FileCheck,
  Loader2,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  const [fileWorkbank, setFileWorkbank] = useState<File | null>(null);
  const [fileBank, setFileBank] = useState<File | null>(null);
  const [bank, setBank] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);

  async function sendToQueue(e: React.FormEvent) {
    e.preventDefault();
    if (!fileWorkbank || !fileBank || !bank) {
      setMessage("Preencha todos os parâmetros antes de iniciar.");
      setIsSuccess(false);
      return;
    }

    setLoading(true);
    setMessage("");

    const uri = "http://192.168.1.90:8001";
    const form = new FormData();
    form.append('fileWork', fileWorkbank);
    form.append('fileBank', fileBank);
    form.append("bank", bank);

    try {
      const response = await axios.post(`${uri}/pricing`, form, { responseType: 'blob' });

      if (response.data.type === "application/json") {
        const text = await response.data.text();
        const errorData = JSON.parse(text);

        setMessage(errorData.message || "O Excel não foi gerado com sucesso.");
        setIsSuccess(false);
        setLoading(false);
        return;
      }

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${bank}_Atualizacoes.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage("Arquivo com as Alterações gerado com sucesso");
      setIsSuccess(true);
    } catch (err) {
      setMessage("Falha na comunicação com o serviço de fila.");
      setIsSuccess(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen w-full bg-[#020617] text-slate-200 flex flex-col font-sans">

      <nav className="w-full border-b border-slate-800 bg-slate-900/20 backdrop-blur-md px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Edição Pricing </h1>
          </div>
        </div>
      </nav>

      <div className="flex-1 p-8 grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-400 mx-auto w-full">

        <div className="group relative bg-slate-900/40 border border-slate-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all flex flex-col">
          <div className="mb-6">
            <h2 className="text-xl font-semibold mt-1">Origem Workbank</h2>
            <p className="text-slate-500 text-sm">Suba o relatório extraído do sistema core.</p>
          </div>

          <div className="flex-1 flex flex-col justify-center border-2 border-dashed border-slate-800 rounded-xl p-3 transition-colors group-hover:bg-slate-950/50">
            <input
              type="file"
              className="hidden"
              id="fileWork"
              onChange={(e) => setFileWorkbank(e.target.files?.[0] || null)}
            />
            <label htmlFor="fileWork" className="cursor-pointer flex flex-col items-center text-center">
              <div className="p-4 bg-slate-800 rounded-full mb-4 group-hover:bg-blue-600/10 group-hover:text-blue-500 transition-all">
                <Upload className="w-8 h-8" />
              </div>
              <p className="text-sm font-medium">
                {fileWorkbank ? fileWorkbank.name : "Arraste ou clique para selecionar"}
              </p>
              <span className="text-xs text-slate-500 mt-2">Formato: .xlsx, .csv</span>
            </label>
          </div>
          <div className="mb-6">
            <h2 className="text-xl font-semibold mt-1">Dados Bancários</h2>
            <p className="text-slate-500 text-sm">Importe o arquivo fornecido pela instituição.</p>
          </div>

          <div className="flex-1 flex flex-col justify-center border-2 border-dashed border-slate-800 rounded-xl p-3 transition-colors group-hover:bg-slate-950/50">
            <input
              type="file"
              className="hidden"
              id="fileBank"
              onChange={(e) => setFileBank(e.target.files?.[0] || null)}
            />
            <label htmlFor="fileBank" className="cursor-pointer flex flex-col items-center text-center">
              <div className="p-4 bg-slate-800 rounded-full mb-4 group-hover:bg-blue-600/10 group-hover:text-blue-500 transition-all">
                <FileCheck className="w-8 h-8" />
              </div>
              <p className="text-sm font-medium">
                {fileBank ? fileBank.name : "Clique para selecionar o banco"}
              </p>
              <span className="text-xs text-slate-500 mt-2">Tamanho máximo: 50MB</span>
            </label>
          </div>
        </div>

        <div className="space-y-6 flex flex-col">
          <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 flex-1">
            <div className="mb-6">
              <h2 className="text-xl font-semibold mt-1">Parâmetros</h2>
              <p className="text-slate-500 text-sm">Defina o destino e execute a rotina.</p>
            </div>

            <div className="space-y-4">
                <label className="block text-xs uppercase font-bold text-slate-500 tracking-widest ml-1">Instituição Alvo</label>
                <select
                    value={bank}
                    onChange={(e) => setBank(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-4 px-4 text-sm text-slate-200 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all"
                >
                    <option value="" disabled>Selecione uma opção...</option>
                    <option value="Capital Consig">Capital Consig</option>
                    <option value="Safra">Safra</option>
                    <option value="Santander">Santander</option>
                </select>

                <div className="pt-4 border-t border-slate-800 mt-6">
                    <button
                        onClick={sendToQueue}
                        disabled={loading}
                        className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-3 transition-all
                            ${loading
                                ? "bg-slate-800 text-slate-500"
                                : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 active:scale-95"}`}
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                        {loading ? "Processando..." : "DISPARAR FILA"}
                    </button>
                </div>
            </div>
          </div>

          {message && (
            <div className={`p-4 rounded-xl border flex items-start gap-3 animate-in fade-in zoom-in duration-300
              ${isSuccess
                ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400"
                : "bg-red-500/5 border-red-500/20 text-red-400"}`}>
              {isSuccess ? <CheckCircle2 className="w-5 h-5 mt-0.5" /> : <AlertCircle className="w-5 h-5 mt-0.5" />}
              <div>
                  <p className="font-bold text-sm">{isSuccess ? "Sucesso" : "Atenção"}</p>
                  <p className="text-xs opacity-80">{message}</p>
              </div>
            </div>
          )}
        </div>

      </div>

      <footer className="w-full px-8 py-4 border-t border-slate-800 bg-slate-900/10 flex justify-between items-center text-[10px] text-slate-600">
        <p>FEITO POR: FERNANDO MORETI BOLELA E SILVA</p>
      </footer>
    </main>
  );
}
