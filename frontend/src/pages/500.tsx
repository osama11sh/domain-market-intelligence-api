export default function ServerError() {
  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-indigo-400 mb-2">500</h1>
        <p className="text-gray-400">Something went wrong on the server.</p>
        <a href="/" className="mt-4 inline-block text-indigo-400 hover:underline">Go home</a> {/* eslint-disable-line @next/next/no-html-link-for-pages */}
      </div>
    </main>
  );
}
