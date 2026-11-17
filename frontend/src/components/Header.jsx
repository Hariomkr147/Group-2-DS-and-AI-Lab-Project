export default function Header({ user, course, onSignOut }) {
  return (
    <header className="app-header">
      <div className="brand">
        <h1>NCERT Socratic Tutor</h1>
        <p>Data Science &amp; AI Lab · IIT Madras BS · Group 2</p>
      </div>
      <div className="header-badges">
        {course && <span className="badge badge-live">{course.title}</span>}
        {user && <span className="badge">{user}</span>}
        {user && <button type="button" className="chip" onClick={onSignOut}>Sign out</button>}
      </div>
    </header>
  );
}
