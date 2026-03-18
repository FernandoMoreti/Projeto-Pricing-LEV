'use client'

import { Upload, FileSpreadsheet, X } from 'lucide-react';
import { useState, useRef } from 'react';

interface FileUploadProps {
  title: string;
  description: string;
  onFileSelect: (file: File | null) => void;
}

export function FileUpload({ title, onFileSelect }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isExcelFile(selectedFile)) {
      setFile(selectedFile);
      onFileSelect(selectedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isExcelFile(droppedFile)) {
      setFile(droppedFile);
      onFileSelect(droppedFile);
    }
  };

  const isExcelFile = (file: File) => {
    const validTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.xlsx',
      '.xls'
    ];
    return validTypes.some(type =>
      file.type === type || file.name.toLowerCase().endsWith(type)
    );
  };

  const handleAreaClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    onFileSelect(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h2 className="text-lg pl-3 font-medium text-white">{title}:</h2>
      </div>

      <div
        onClick={handleAreaClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border rounded-3xl p-10 cursor-pointer
          transition-all duration-200 ease-in-out
          ${isDragging
            ? 'border-cyan-400 bg-cyan-500/10 shadow-[0_0_20px_rgba(34,211,238,0.3)]'
            : 'border-neutral-700 bg-black/40 hover:border-cyan-500/50 hover:shadow-[0_0_15px_rgba(34,211,238,0.2)]'
          }
        `}
      >
        {!file ? (
          <div className="flex flex-col items-center gap-3 text-center">
            <div className={`
              p-2.5 transition-all duration-200
              ${isDragging ? 'bg-linear-to-r from-cyan-500 to-purple-500' : 'bg-neutral-800'}
            `}>
              <Upload
                className={`
                  w-5 h-5 transition-colors duration-200
                  ${isDragging ? 'text-white' : 'text-cyan-400'}
                `}
              />
            </div>
            <div>
              <p className="text-xs text-neutral-300 mb-1">
                Arraste ou <span className="text-cyan-400 font-medium">clique aqui</span> para subir o Excel
              </p>
              <p className="text-[10px] text-neutral-500 uppercase tracking-widest">XLSX, XLS</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-linear-to-r rounded-xl from-cyan-500 to-purple-500">
                <FileSpreadsheet className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="font-medium text-xs text-white truncate">{file.name}</p>
                <p className="text-xs text-neutral-400">
                  {(file.size / 1024).toFixed(2)} KB
                </p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              className="p-1.5 rounded-xl hover:bg-neutral-800 transition-colors duration-150 z-10"
              aria-label="Remover arquivo"
            >
              <X className="w-4 h-4 text-neutral-400 hover:text-pink-400" />
            </button>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>
    </div>
  );
}