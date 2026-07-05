import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export default function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  // Escape key handler & focus management
  useEffect(() => {
    if (isOpen) {
      previousFocus.current = document.activeElement as HTMLElement;
      
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };
      
      window.addEventListener('keydown', handleKeyDown);
      
      // Auto-focus container or first input
      if (modalRef.current) {
        const focusable = modalRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length > 0) {
          (focusable[0] as HTMLElement).focus();
        }
      }

      return () => {
        window.removeEventListener('keydown', handleKeyDown);
        if (previousFocus.current) {
          previousFocus.current.focus();
        }
      };
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      {/* Background Backdrop */}
      <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-sm transition-opacity" onClick={onClose} />

      {/* Modal Container */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div 
          ref={modalRef}
          className="relative transform overflow-hidden rounded-lg bg-white border border-neutral-200 text-left shadow-xl transition-all w-full max-w-lg p-6 space-y-4"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
            <h3 id="modal-title" className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
              {title}
            </h3>
            <button
              onClick={onClose}
              className="p-1 rounded-full text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
              title="Close modal"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body Content */}
          <div className="text-xs text-neutral-600 space-y-3">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
