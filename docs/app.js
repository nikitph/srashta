'use strict';
// An illustrative, authored graph. No planning or execution runs in this page.
const tickets = {
  'C-01': {
    kind: 'CONTRACT', wave: 0, title: 'Define the Notes contract',
    description: 'Establish the shared schema and API response shape before feature work begins.',
    dependencies: 'No prerequisites',
    paths: ['app/Modules/Notes/Note.php', 'database/migrations/*_create_notes_table.php'],
    acceptance: ['A note has an integer ID, title and timestamps.', 'The title is required and limited to 120 characters.', 'The approved contract defines create, read and error responses.']
  },
  'T-01': {
    kind: 'FEATURE', wave: 1, title: 'Create a note',
    description: 'Implement POST /api/notes against the approved contract. Own the write path and its tests.',
    dependencies: 'C-01 · Notes contract',
    paths: ['app/Modules/Notes/CreateNote.php', 'app/Http/Controllers/Api/CreateNoteController.php', 'routes/api/notes-create.php', 'tests/Feature/Notes/CreateNoteTest.php'],
    acceptance: ['A valid title persists a note and returns HTTP 201 with an integer ID.', 'Missing or overlong titles return HTTP 422.', 'An invalid request does not persist a note.']
  },
  'T-02': {
    kind: 'FEATURE', wave: 1, title: 'Read a note',
    description: 'Implement GET /api/notes/{id}. Separate controller and route fragments keep its file scope independent from the write ticket.',
    dependencies: 'C-01 · Notes contract',
    paths: ['app/Http/Controllers/Api/ReadNoteController.php', 'routes/api/notes-read.php', 'tests/Feature/Notes/ReadNoteTest.php'],
    acceptance: ['An existing note returns HTTP 200 with its integer ID and title.', 'An unknown ID returns HTTP 404.', 'The response matches the approved Notes contract.']
  },
  'I-01': {
    kind: 'INTEGRATION', wave: 2, title: 'Create → retrieve',
    description: 'Exercise the complete API journey after both feature tickets have landed. Check that the pieces agree in use.',
    dependencies: 'T-01 · Create a note; T-02 · Read a note',
    paths: ['tests/Feature/Notes/NoteJourneyTest.php'],
    acceptance: ['Create a note, then retrieve it using the returned ID.', 'The retrieved title and ID match the created note.', 'The journey passes against persisted data, not a mocked response.']
  }
};
const byId = id => document.getElementById(id);
document.querySelectorAll('[data-ticket]').forEach(button => {
  button.addEventListener('click', () => {
    const id = button.dataset.ticket;
    const ticket = tickets[id];
    document.querySelectorAll('[data-ticket]').forEach(other => {
      const selected = other === button;
      other.classList.toggle('selected', selected);
      other.setAttribute('aria-pressed', String(selected));
    });
    byId('brief-kind').textContent = `${id} / ${ticket.kind}`;
    byId('brief-wave').textContent = `WAVE ${ticket.wave}`;
    byId('brief-title').textContent = ticket.title;
    byId('brief-description').textContent = ticket.description;
    byId('brief-dependencies').textContent = ticket.dependencies;
    byId('brief-paths').replaceChildren(...ticket.paths.map(path => {
      const code = document.createElement('code');
      code.textContent = path;
      return code;
    }));
    byId('brief-acceptance').replaceChildren(...ticket.acceptance.map(text => {
      const li = document.createElement('li');
      li.textContent = text;
      return li;
    }));
  });
});
let copyReset;
byId('copy').addEventListener('click', async () => {
  const button = byId('copy');
  clearTimeout(copyReset);
  try {
    await navigator.clipboard.writeText(byId('install-code').textContent);
    button.textContent = 'Copied!';
    byId('copy-status').textContent = 'Quickstart commands copied to clipboard.';
  } catch {
    button.textContent = 'Select text';
    const range = document.createRange();
    range.selectNodeContents(byId('install-code'));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    byId('copy-status').textContent = 'Automatic copy unavailable. Commands selected; press your copy shortcut.';
  }
  copyReset = setTimeout(() => { button.textContent = 'Copy'; }, 2500);
});
