export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="mt-2 text-muted-foreground">Return to KrowLive dashboard.</p>
        <a href="/" className="mt-4 inline-block text-violet-400 hover:underline">
          Go home
        </a>
      </div>
    </main>
  );
}
