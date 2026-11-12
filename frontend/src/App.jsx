import { useEffect, useRef } from "react";

import {
  matchPath,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import Header from "./components/Header";
import AuthPage from "./pages/AuthPage";
import ProfilePage from "./pages/ProfilePage";
import TripsPage from "./pages/TripsPage";
import NewTripPage from "./pages/NewTripPage";
import PlacesPage from "./pages/PlacesPage";

const routes = [
  { path: "/viagens", title: "Minhas viagens" },
  { path: "/viagens/nova", title: "Planejar viagem" },
  { path: "/viagens/:tripId", title: "Roteiro" },
  {
    path: "/viagens/:tripId/lugares",
    title: "Lugares da viagem",
  },
  {
    path: "/viagens/:tripId/orcamento",
    title: "Orçamento",
  },
  {
    path: "/viagens/:tripId/grupo",
    title: "Grupo",
  },
  {
    path: "/viagens/:tripId/destino",
    title: "Destino do grupo",
  },
  { path: "/lugares", title: "Meus lugares" },
  { path: "/amigos", title: "Amigos" },
  { path: "/conta", title: "Minha conta" },
  { path: "/conta/seguranca", title: "Segurança" },
  {
    path: "/conta/historico",
    title: "Histórico de viagens",
  },
  { path: "/entrar", title: "Entrar" },
  { path: "/cadastro", title: "Cadastro" },
  { path: "/ajuda", title: "Ajuda" },
];

function AppLayout() {
  const location = useLocation();
  const mainRef = useRef(null);
  const firstRender = useRef(true);

  useEffect(() => {
    const currentRoute = routes.find((route) =>
      matchPath(
        { path: route.path, end: true },
        location.pathname,
      ),
    );

    document.title = currentRoute
      ? `${currentRoute.title} · Rumo`
      : "Rumo";

    if (!firstRender.current) {
      mainRef.current?.focus();
      window.scrollTo(0, 0);
    }

    firstRender.current = false;
  }, [location.pathname]);

  return (
    <>
      <a href="#conteudo" className="skip-link">
        Pular para o conteúdo
      </a>

      <Header />

      <main
        id="conteudo"
        ref={mainRef}
        tabIndex={-1}
        className="page-container"
      >
        <Outlet />
      </main>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route
          index
          element={<Navigate to="/viagens" replace />}
        />

        {routes.map((route) => (
          <Route
            key={route.path}
            path={route.path}
            element={
              route.path === "/viagens" ? (
                <TripsPage key="trips" />
              ) : route.path === "/viagens/nova" ? (
                <NewTripPage />
              ) : route.path === "/conta/historico" ? (
                <TripsPage key="history" history />
              ) : route.path === "/entrar" ? (
                <AuthPage key="login" mode="login" />
              ) : route.path === "/cadastro" ? (
                <AuthPage
                  key="register"
                  mode="register"
                />
              ) : route.path === "/conta" ? (
                <ProfilePage />
              ) : route.path === "/lugares" ? (
                <PlacesPage />
              ) : (
                <></>
              )
            }
          />
        ))}

        <Route path="*" element={<></>} />
      </Route>
    </Routes>
  );
}