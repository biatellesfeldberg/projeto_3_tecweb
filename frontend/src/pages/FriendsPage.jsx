import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";

import { Avatar, Badge, Button, Field, PageHeading } from "../components/ui";
import Feedback from "../components/Feedback";
import Modal from "../components/Modal";
import { useAuth } from "../contexts/AuthContext";

import {
  acceptFriendRequest,
  cancelFriendRequest,
  listFriendRequests,
  listFriends,
  rejectFriendRequest,
  removeFriend,
  searchPeople,
  sendFriendRequest,
} from "../services/friends";

import "./friends.css";

function personName(person) {
  return (
    [person.first_name, person.last_name].filter(Boolean).join(" ") ||
    "Pessoa sem nome"
  );
}

function errorMessage(error) {
  return (
    Object.values(error.fields || {})
      .filter(Boolean)
      .join(" ") ||
    error.message ||
    "Não foi possível concluir. Tente novamente."
  );
}

function Person({ person, children }) {
  const initials =
    `${person.first_name?.[0] || ""}${person.last_name?.[0] || ""}`.toUpperCase() ||
    "?";

  return (
    <li className="friend-person">
      <div className="friend-identity">
        <span aria-hidden="true">
          <Avatar initials={initials} />
        </span>

        <h3>{personName(person)}</h3>
      </div>

      <div className="friend-actions">{children}</div>
    </li>
  );
}

export default function FriendsPage() {
  const { user, isRestoring, expireSession } = useAuth();

  if (isRestoring) {
    return <Feedback kind="loading" title="Verificando sua sessão…" />;
  }

  if (!user) {
    return <Navigate to="/entrar" replace />;
  }

  // Trocar de conta descarta todas as listas e requisições da conta anterior.
  return (
    <FriendsContent
      key={user.id}
      userId={user.id}
      expireSession={expireSession}
    />
  );
}

function FriendsContent({ userId, expireSession }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [revision, setRevision] = useState(0);

  const [tab, setTab] = useState("friends");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searched, setSearched] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const [busy, setBusy] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [removing, setRemoving] = useState(null);

  const inputRef = useRef(null);
  const searchRef = useRef(null);
  const actionRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setLoadError("");

    Promise.all([
      listFriends({ signal: controller.signal }),
      listFriendRequests({ signal: controller.signal }),
    ])
      .then(([friends, requests]) => {
        if (controller.signal.aborted) return;

        if (
          !Array.isArray(friends) ||
          !Array.isArray(requests.received) ||
          !Array.isArray(requests.sent)
        ) {
          throw new Error(
            "O servidor retornou listas de amizades em um formato inesperado.",
          );
        }

        setData({ friends, ...requests });
      })
      .catch((error) => {
        if (controller.signal.aborted) return;

        if (error.status === 401) {
          expireSession();
        } else {
          setLoadError(errorMessage(error));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [revision, expireSession]);

  useEffect(
    () => () => {
      searchRef.current?.abort();
      actionRef.current?.abort();
    },
    [],
  );

  const disabled = loading || Boolean(loadError) || Boolean(busy) || !data;
  const requestCount = data ? data.received.length + data.sent.length : 0;

  function changeQuery(value) {
    searchRef.current?.abort();
    searchRef.current = null;

    setQuery(value);
    setResults(null);
    setSearching(false);
    setSearchError("");
  }

  async function search(event) {
    event.preventDefault();

    if (disabled) return;

    const term = query.trim();

    if (term.length < 2) {
      setSearchError("Digite pelo menos dois caracteres para buscar.");
      inputRef.current?.focus();
      return;
    }

    searchRef.current?.abort();

    const controller = new AbortController();
    searchRef.current = controller;

    setSearching(true);
    setSearchError("");
    setResults(null);
    setSearched(term);

    try {
      const people = await searchPeople(term, {
        signal: controller.signal,
      });

      if (controller.signal.aborted) return;

      if (!Array.isArray(people)) {
        throw new Error(
          "O servidor retornou uma busca em formato inesperado.",
        );
      }

      setResults(
        people.filter((person) => person.id !== userId),
      );
    } catch (error) {
      if (controller.signal.aborted) return;

      if (error.status === 401) {
        expireSession();
      } else {
        setSearchError(errorMessage(error));
      }
    } finally {
      if (!controller.signal.aborted) {
        searchRef.current = null;
        setSearching(false);
      }
    }
  }

  async function act(kind, person, requestId) {
    if (actionRef.current || disabled) return;

    const controller = new AbortController();
    actionRef.current = controller;

    setBusy(`${kind}-${person.id}`);
    setActionError("");
    setNotice("");

    try {
      const options = {
        signal: controller.signal,
      };

      const operations = {
        send: () => sendFriendRequest(person.id, options),
        accept: () => acceptFriendRequest(requestId, options),
        reject: () => rejectFriendRequest(requestId, options),
        cancel: () => cancelFriendRequest(requestId, options),
        remove: () => removeFriend(person.id, options),
      };

      const created = await operations[kind]();

      if (controller.signal.aborted) return;

      setData((current) => {
        if (kind === "send") {
          return {
            ...current,
            sent: [created, ...current.sent],
          };
        }

        if (kind === "accept") {
          return {
            ...current,
            received: current.received.filter(
              (item) => item.id !== requestId,
            ),
            friends: [
              ...current.friends.filter(
                (item) => item.id !== person.id,
              ),
              person,
            ],
          };
        }

        if (kind === "reject") {
          return {
            ...current,
            received: current.received.filter(
              (item) => item.id !== requestId,
            ),
          };
        }

        if (kind === "cancel") {
          return {
            ...current,
            sent: current.sent.filter(
              (item) => item.id !== requestId,
            ),
          };
        }

        return {
          ...current,
          friends: current.friends.filter(
            (item) => item.id !== person.id,
          ),
        };
      });

      const messages = {
        send: `Solicitação enviada para ${personName(person)}.`,
        accept: `Agora você e ${personName(person)} são amigos.`,
        reject: `Solicitação de ${personName(person)} recusada.`,
        cancel: `Solicitação para ${personName(person)} cancelada.`,
        remove: `Amizade com ${personName(person)} removida.`,
      };

      setNotice(messages[kind]);

      if (kind === "remove") {
        setRemoving(null);
      }
    } catch (error) {
      if (controller.signal.aborted) return;

      if (error.status === 401) {
        expireSession();
      } else {
        setActionError(errorMessage(error));

        // Outra aba/pessoa pode ter respondido ou removido a solicitação.
        if (error.status === 400 || error.status === 404) {
          setRevision((value) => value + 1);
        }
      }
    } finally {
      if (!controller.signal.aborted) {
        actionRef.current = null;
        setBusy("");
      }
    }
  }

  function actionsFor(person) {
    if (
      data.friends.some(
        (item) => item.id === person.id,
      )
    ) {
      return <Badge>Já é amigo</Badge>;
    }

    const received = data.received.find(
      (item) => item.sender.id === person.id,
    );

    if (received) {
      return (
        <>
          <Button
            disabled={disabled}
            onClick={() => act("accept", person, received.id)}
            aria-label={`Aceitar solicitação de ${personName(person)}`}
          >
            Aceitar
          </Button>

          <Button
            variant="secondary"
            disabled={disabled}
            onClick={() => act("reject", person, received.id)}
            aria-label={`Recusar solicitação de ${personName(person)}`}
          >
            Recusar
          </Button>
        </>
      );
    }

    const sent = data.sent.find(
      (item) => item.recipient.id === person.id,
    );

    if (sent) {
      return (
        <>
          <Badge>Solicitação enviada</Badge>

          <Button
            variant="secondary"
            disabled={disabled}
            onClick={() => act("cancel", person, sent.id)}
            aria-label={`Cancelar solicitação para ${personName(person)}`}
          >
            Cancelar solicitação
          </Button>
        </>
      );
    }

    return (
      <Button
        disabled={disabled}
        onClick={() => act("send", person)}
        aria-label={`Adicionar ${personName(person)}`}
      >
        Adicionar
      </Button>
    );
  }

  return (
    <div className="friends-page">
      <PageHeading
        eyebrow="Boas companhias"
        title="Com quem você quer ir?"
        description="Encontre pessoas e organize suas amizades."
        action={
          <Button onClick={() => inputRef.current?.focus()}>
            + Adicionar amigo
          </Button>
        }
      />

      {notice && (
        <Feedback kind="success" title={notice} />
      )}

      {actionError && !removing && (
        <Feedback
          kind="error"
          title="Não foi possível concluir a ação."
          detail={actionError}
        />
      )}

      <section
        className="card friends-search"
        aria-labelledby="friends-search-heading"
      >
        <h2 id="friends-search-heading">Buscar pessoas</h2>

        <form
          className="friends-search-form"
          onSubmit={search}
          role="search"
          aria-label="Buscar pessoas"
        >
          <Field
            id="friends-query"
            label="Nome ou e-mail completo"
            hint="Use pelo menos dois caracteres. A busca retorna até 20 pessoas."
            error={searchError}
          >
            <input
              id="friends-query"
              ref={inputRef}
              value={query}
              onChange={(event) => changeQuery(event.target.value)}
              type="search"
              maxLength={254}
              autoComplete="off"
              aria-invalid={Boolean(searchError)}
              aria-describedby={`friends-query-hint${searchError ? " friends-query-error" : ""}`}
            />
          </Field>

          <Button
            type="submit"
            disabled={disabled || searching}
          >
            {searching ? "Buscando…" : "Buscar"}
          </Button>

          {(query || results) && (
            <Button
              variant="ghost"
              onClick={() => {
                changeQuery("");
                inputRef.current?.focus();
              }}
            >
              Limpar
            </Button>
          )}
        </form>

        {searching && (
          <Feedback kind="loading" title="Buscando pessoas…" />
        )}

        {results && data && !searching && (
          <div className="friends-search-results">
            <p role="status">
              {results.length} resultado(s) para “{searched}”.
            </p>

            {results.length === 0 ? (
              <Feedback
                kind="empty"
                title="Nenhuma pessoa encontrada."
                detail="Tente outro nome ou informe o e-mail completo."
              />
            ) : (
              <ul
                className="friends-list"
                aria-label="Resultados da busca"
              >
                {results.map((person) => (
                  <Person key={person.id} person={person}>
                    {actionsFor(person)}
                  </Person>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {loading ? (
        <Feedback
          kind="loading"
          title="Carregando amigos e solicitações…"
        />
      ) : loadError ? (
        <Feedback
          kind="error"
          title="Não foi possível carregar suas conexões."
          detail={loadError}
          onRetry={() => setRevision((value) => value + 1)}
        />
      ) : (
        data && (
          <>
            <nav
              className="friends-tabs"
              aria-label="Listas de amizades"
            >
              <Button
                variant={tab === "friends" ? "primary" : "secondary"}
                aria-pressed={tab === "friends"}
                onClick={() => setTab("friends")}
              >
                Meus amigos ({data.friends.length})
              </Button>

              <Button
                variant={tab === "requests" ? "primary" : "secondary"}
                aria-pressed={tab === "requests"}
                onClick={() => setTab("requests")}
              >
                Solicitações ({requestCount})
              </Button>

              <Button
                variant="ghost"
                disabled={Boolean(busy)}
                onClick={() => setRevision((value) => value + 1)}
              >
                Atualizar listas
              </Button>
            </nav>

            {tab === "friends" ? (
              <section
                className="card"
                aria-labelledby="friends-list-heading"
              >
                <h2 id="friends-list-heading">Meus amigos</h2>

                {data.friends.length === 0 ? (
                  <Feedback
                    kind="empty"
                    title="Sua lista de amigos está vazia."
                    detail="Busque uma pessoa pelo nome ou e-mail e envie uma solicitação."
                  />
                ) : (
                  <ul
                    className="friends-list"
                    aria-label="Meus amigos"
                  >
                    {data.friends.map((person) => (
                      <Person key={person.id} person={person}>
                        <Button
                          variant="secondary"
                          disabled={disabled}
                          onClick={() => {
                            setRemoving(person);
                            setActionError("");
                          }}
                          aria-label={`Remover amizade com ${personName(person)}`}
                        >
                          Remover amizade
                        </Button>
                      </Person>
                    ))}
                  </ul>
                )}
              </section>
            ) : (
              <div className="friends-requests-grid">
                <section
                  className="card"
                  aria-labelledby="friends-received-heading"
                >
                  <h2 id="friends-received-heading">
                    Solicitações recebidas
                  </h2>

                  {data.received.length === 0 ? (
                    <Feedback
                      kind="empty"
                      title="Nenhuma solicitação recebida."
                    />
                  ) : (
                    <ul
                      className="friends-list"
                      aria-label="Solicitações recebidas"
                    >
                      {data.received.map((item) => (
                        <Person
                          key={item.id}
                          person={item.sender}
                        >
                          {actionsFor(item.sender)}
                        </Person>
                      ))}
                    </ul>
                  )}
                </section>

                <section
                  className="card"
                  aria-labelledby="friends-sent-heading"
                >
                  <h2 id="friends-sent-heading">
                    Solicitações enviadas
                  </h2>

                  {data.sent.length === 0 ? (
                    <Feedback
                      kind="empty"
                      title="Nenhuma solicitação enviada."
                    />
                  ) : (
                    <ul
                      className="friends-list"
                      aria-label="Solicitações enviadas"
                    >
                      {data.sent.map((item) => (
                        <Person
                          key={item.id}
                          person={item.recipient}
                        >
                          {actionsFor(item.recipient)}
                        </Person>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            )}
          </>
        )
      )}

      {busy && (
        <p role="status" className="muted">
          Salvando alteração…
        </p>
      )}

      <Modal
        open={Boolean(removing)}
        title="Remover amizade"
        onClose={() => {
          if (!busy) setRemoving(null);
        }}
      >
        {removing && (
          <>
            <p>
              Remover {personName(removing)} da sua lista de amigos?
            </p>

            {actionError && (
              <p className="field-error" role="alert">
                {actionError}
              </p>
            )}

            <div className="action-row">
              <Button
                variant="secondary"
                disabled={Boolean(busy)}
                onClick={() => setRemoving(null)}
                data-autofocus
              >
                Manter amizade
              </Button>

              <Button
                className="friends-danger"
                disabled={disabled}
                onClick={() => act("remove", removing)}
              >
                {busy ? "Removendo…" : "Confirmar remoção"}
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}