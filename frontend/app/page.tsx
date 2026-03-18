'use client'

import { useState } from 'react';
import { FileUpload } from './components/fileUploader';
import { CheckCircle2, Loader2 } from 'lucide-react';

export default function App() {
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleProcess = () => {
    if (bankFile) {
      setIsProcessing(true);
      setTimeout(() => {
        setIsProcessing(false);
        setShowSuccess(true);
        setTimeout(() => setShowSuccess(false), 3000);
      }, 1500);
    }
  };

  const canProcess = bankFile;

  return (
    <div className="min-h-screen bg-black">
      <header className="border-b border-neutral-800 bg-black/50 backdrop-blur-sm">
        <div className="mx-auto px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="w-0.5 h-10 bg-linear-to-b from-cyan-400 to-purple-500"></div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight bg-linear-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">LEV NEGÓCIOS</h1>
              <p className="text-sm text-neutral-500">Pricing</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-semibold mb-1 tracking-tight text-white">
            Análise de Planilhas
          </h2>
          <div className="w-32 h-0.5 bg-linear-to-r from-cyan-500 to-purple-500 mb-2"></div>
          <p className="text-sm text-neutral-400">
            Upload dos arquivos Excel para Fila de Processamento
          </p>
        </div>

        <div className="grid gap-6 mb-8">
          <FileUpload
            title="Arquivo do Banco"
            description="Planilha recebida do banco"
            onFileSelect={setBankFile}
          />
        </div>

        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleProcess}
            disabled={!canProcess || isProcessing}
            className={`
              px-8 py-2.5 text-xs rounded-xl font-medium tracking-wide uppercase
              transition-all duration-150 ease-in-out
              ${canProcess && !isProcessing
                ? 'bg-linear-to-r from-blue-600 to-purple-500 text-white border border-transparent hover:shadow-[0_0_30px_rgba(34,211,238,0.6)] hover:scale-105'
                : 'bg-neutral-800 text-neutral-500 cursor-not-allowed border border-neutral-700'
              }
            `}
          >
            {isProcessing ? (
              <span className="flex items-center gap-2">
                <Loader2 className="animate-spin"/>
                Processando
              </span>
            ) : (
              'Processar'
            )}
          </button>

          {showSuccess && (
            <div className="flex rounded-xl items-center gap-2 bg-linear-to-r from-cyan-500 to-purple-500 text-white px-4 py-2 text-xs animate-in fade-in slide-in-from-bottom-2 duration-200 shadow-[0_0_30px_rgba(34,211,238,0.5)]">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Enviado com sucesso</span>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}