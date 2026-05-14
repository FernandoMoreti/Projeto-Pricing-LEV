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
  const [fileAtt, setFileAtt] = useState<File | null>(null);
  const [bank, setBank] = useState<string>("");
  const [bankWork, setBankWork] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);

  async function sendToEdit(e: React.FormEvent) {
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

  async function inputInWorkbank(e: React.FormEvent) {
    e.preventDefault()

    if (!fileAtt || !bankWork) {
      setMessage("Preencha todos os parâmetros antes de iniciar.");
      setIsSuccess(false);
      return;
    }

    setLoading(true);
    setMessage("");

    const uri = "http://192.168.1.90:8001";
    const form = new FormData();

    form.append("fileAtt", fileAtt)
    form.append("bankWork", bankWork)

    try {
      const response = await axios.post(`${uri}/input`, form)

      console.log(response.data)
    } catch (err) {
      console.error(err)
      return err
    } finally {
      setLoading(false)
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
            <h1 className="text-xl font-bold tracking-tight">Edição Pricing</h1>
          </div>
        </div>
      </nav>

      <div className="flex-1 p-8 max-w-[80%] mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all flex flex-col gap-6">
            <div>
              <h2 className="text-xl font-semibold">Tabelas do Workbank</h2>
              <p className="text-slate-500 text-sm mb-4">Suba o relatório extraído do sistema Workbank.</p>
              <div className="border-2 border-dashed border-slate-800 rounded-xl p-8 hover:border-blue-500/30 transition-all hover:bg-slate-950/50">
                <input
                  type="file"
                  className="hidden"
                  id="fileWork"
                  onChange={(e) => setFileWorkbank(e.target.files?.[0] || null)}
                />
                <label htmlFor="fileWork" className="cursor-pointer flex flex-col items-center text-center">
                  <Upload className="w-8 h-8 mb-3 text-slate-400" />
                  <p className="text-sm font-medium">
                    {fileWorkbank ? fileWorkbank.name : "Arraste ou clique para selecionar"}
                  </p>
                  <span className="text-xs text-slate-500 mt-2">Formato: .xlsx, .csv</span>
                </label>
              </div>
            </div>

            <div>
              <h2 className="text-xl font-semibold">Tabela Atualizada do Banco</h2>
              <p className="text-slate-500 text-sm mb-4">Importe o arquivo fornecido pela instituição.</p>
              <div className="border-2 border-dashed border-slate-800 rounded-xl p-8 hover:border-blue-500/30 transition-all hover:bg-slate-950/50">
                <input
                  type="file"
                  className="hidden"
                  id="fileBank"
                  onChange={(e) => setFileBank(e.target.files?.[0] || null)}
                />
                <label htmlFor="fileBank" className="cursor-pointer flex flex-col items-center text-center">
                  <FileCheck className="w-8 h-8 mb-3 text-slate-400" />
                  <p className="text-sm font-medium">
                    {fileBank ? fileBank.name : "Clique para selecionar o banco"}
                  </p>
                  <span className="text-xs text-slate-500 mt-2">Tamanho máximo: 50MB</span>
                </label>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-6">
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-xl font-semibold mb-4">Selecionar para Edição</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2 ml-1">Instituição Alvo</label>
                  <select
                    value={bank}
                    onChange={(e) => setBank(e.target.value)}
                    className="w-full mb-5 bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all"
                  >
                    <option value="" disabled>Selecione uma opção...</option>
                    <option value="Amigoz">Amigoz</option>
                    <option value="Capital Consig">Capital Consig</option>
                    <option value="Pan">Pan</option>
                    <option value="PanLafy">PanLafy</option>
                    <option value="Safra">Safra</option>
                    <option value="Santander">Santander</option>
                    <option value="Ole">Ole</option>
                  </select>

                  <button
                    onClick={sendToEdit}
                    disabled={loading}
                    className={`w-full mb-5 py-4 rounded-xl font-bold flex items-center justify-center gap-3 transition-all
                      ${loading ? "bg-slate-800 text-slate-500" : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 active:scale-95"}`}
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                    {loading ? "EDITANDO..." : "INICIAR EDIÇÃO"}
                  </button>
                </div>
              </div>

              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 mb-5">
                <h2 className="text-xl font-semibold mb-4">Entrada no Workbank</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
                  <div className="flex flex-col gap-2">
                    <label className="block text-[10px] uppercase font-bold text-slate-500 tracking-widest ml-1">Instituição</label>
                    <select
                      value={bankWork}
                      onChange={(e) => setBankWork(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all"
                    >
                      <option value="" disabled>Selecione...</option>
                      <option value="Amigoz">Amigoz</option>
                      <option value="Capital Consig">Capital Consig</option>
                      <option value="Pan">Pan</option>
                      <option value="PanLafy">PanLafy</option>
                      <option value="Safra">Safra</option>
                      <option value="Santander">Santander</option>
                      <option value="Ole">Ole</option>
                    </select>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="block text-[10px] uppercase font-bold text-slate-500 tracking-widest ml-1">Arquivo Input</label>
                    <div className="border-2 border-dashed border-slate-800 rounded-xl h-13.5 flex items-center hover:border-blue-500/30 transition-all hover:bg-slate-950/50">
                      <input
                        type="file"
                        className="hidden"
                        id="fileAtt"
                        onChange={(e) => setFileAtt(e.target.files?.[0] || null)}
                      />
                      <label htmlFor="fileAtt" className="cursor-pointer w-full text-center truncate">
                        <p className="text-xs font-medium text-slate-400">
                          {fileAtt ? fileAtt.name : "Clique p/ anexar"}
                        </p>
                      </label>
                    </div>
                  </div>
                </div>

                <button
                  onClick={inputInWorkbank}
                  disabled={loading}
                  className={`w-full mt-4 py-4 rounded-xl font-bold flex items-center justify-center gap-3 transition-all
                    ${loading ? "bg-slate-800 text-slate-500" : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20 active:scale-95"}`}
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                  {loading ? "INPUTANDO..." : "ENVIAR PARA O WORKBANK"}
                </button>
              </div>

              {message && (
                <div className={`p-4 rounded-xl border flex items-start gap-3 animate-in fade-in zoom-in duration-300
                  ${isSuccess ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400" : "bg-red-500/5 border-red-500/20 text-red-400"}`}>
                  {isSuccess ? <CheckCircle2 className="w-5 h-5 mt-0.5" /> : <AlertCircle className="w-5 h-5 mt-0.5" />}
                  <div>
                    <p className="font-bold text-sm">{isSuccess ? "Sucesso" : "Atenção"}</p>
                    <p className="text-xs opacity-80">{message}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <footer className="w-full px-8 py-4 border-t border-slate-800 bg-slate-900/10 flex justify-between items-center text-[10px] text-slate-600 mt-auto">
        <p>FEITO POR: FERNANDO MORETI BOLELA E SILVA</p>
      </footer>
    </main>
  );
}
