import { useEffect, useId, useRef } from "react";

import "./modal.css";

/*
  Janela sobreposta acessível, baseada no <dialog> nativo:
  o navegador prende o foco dentro dela, fecha com Esc e escurece o fundo.
  O conteúdo só é montado enquanto a janela está aberta, então formulários
  voltam ao estado inicial a cada abertura.
*/
export default function Modal({
  open,
  title,
  description,
  onClose,
  size = "medium",
  children,
}) {
  const ref = useRef(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      dialog.showModal();
      // Campo marcado com data-autofocus recebe o foco ao abrir.
      dialog.querySelector("[data-autofocus]")?.focus();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`modal modal--${size}`}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        // Clique no fundo escurecido (fora do conteúdo) fecha a janela.
        if (event.target === ref.current) {
          onClose();
        }
      }}
    >
      {open && (
        <div className="modal-content">
          <header className="modal-header">
            <div>
              <h2 id={titleId}>{title}</h2>

              {description && (
                <p id={descriptionId} className="muted">
                  {description}
                </p>
              )}
            </div>

            <button
              type="button"
              className="modal-close"
              onClick={onClose}
              aria-label="Fechar"
            >
              ×
            </button>
          </header>

          {children}
        </div>
      )}
    </dialog>
  );
}
