"""Reproducible local idea-to-API acceptance fixture. Creates a NEW Laravel project.

Run: python examples/notes_demo.py /absolute/path/to/new-notes-demo
Fixture approvals explicitly identify themselves; they are not real product approvals.
"""
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import yaml
from srashta.common import write_json

PRD = '''# Notes API — acceptance fixture

## FR-NOTE-001 [P0] Create a note
A client can persist a note with a nonempty title of at most 120 characters.

Acceptance criteria
WHEN a client submits a valid title, THE SYSTEM SHALL persist the note and return HTTP 201 with its integer id and title.
IF the title is missing or exceeds 120 characters, THE SYSTEM SHALL return HTTP 422 and persist nothing.

## FR-NOTE-002 [P0] Read a note
A client can retrieve a previously created note by id.

Acceptance criteria
WHEN a client requests an existing note, THE SYSTEM SHALL return HTTP 200 with its id and title.
IF the note id does not exist, THE SYSTEM SHALL return HTTP 404.
'''
CONTRACT = '''# Approved example design
Notes have an integer id, title (maximum 120 characters), and timestamps. No authentication
is required in this local acceptance fixture. This example is not a production service.
POST /api/notes accepts title and returns {data:{id,title}} with status 201.
GET /api/notes/{note} returns the same resource with status 200; missing id returns 404.
Laravel validation returns 422. Controllers delegate writes to CreateNote; model binding
handles lookup. Shared routes/api.php loads per-module fragments. SQLite is the test store.
'''
CONTRACT_FILES = {
'app/Modules/Notes/Note.php': '''<?php
namespace App\\Modules\\Notes;
use Illuminate\\Database\\Eloquent\\Model;
class Note extends Model
{
    protected $fillable = ['title'];
}
''',
'database/migrations/2026_01_01_000000_create_notes_table.php': '''<?php
use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;
return new class extends Migration {
    public function up(): void { Schema::create('notes', function (Blueprint $table) {
        $table->id(); $table->string('title', 120); $table->timestamps();
    }); }
    public function down(): void { Schema::dropIfExists('notes'); }
};
''',
'routes/api.php': '''<?php
use Illuminate\\Http\\Request;
use Illuminate\\Support\\Facades\\Route;
Route::get('/user', function (Request $request) { return $request->user(); })->middleware('auth:sanctum');
foreach (glob(__DIR__.'/api/*.php') as $fragment) { require $fragment; }
''',
 'tests/Feature/Notes/SchemaTest.php': '''<?php
use App\\Modules\\Notes\\Note;
it('persists a note through the frozen schema', function () {
    $note = Note::create(['title' => 'Contract fixture']);
    expect($note->fresh()->title)->toBe('Contract fixture');
    $this->assertDatabaseCount('notes', 1);
});
'''}
FEATURE_FILES = {
'app/Modules/Notes/CreateNote.php': '''<?php
namespace App\\Modules\\Notes;
class CreateNote
{
    public function execute(string $title): Note { return Note::create(['title' => $title]); }
}
''',
'app/Http/Requests/StoreNoteRequest.php': '''<?php
namespace App\\Http\\Requests;
use Illuminate\\Foundation\\Http\\FormRequest;
class StoreNoteRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array { return ['title' => ['required', 'string', 'max:120']]; }
}
''',
'app/Http/Resources/NoteResource.php': '''<?php
namespace App\\Http\\Resources;
use Illuminate\\Http\\Request;
use Illuminate\\Http\\Resources\\Json\\JsonResource;
/** @mixin \\App\\Modules\\Notes\\Note */
class NoteResource extends JsonResource
{
    public function toArray(Request $request): array { return ['id' => $this->id, 'title' => $this->title]; }
}
''',
'app/Http/Controllers/Api/NoteController.php': '''<?php
namespace App\\Http\\Controllers\\Api;
use App\\Http\\Controllers\\Controller;
use App\\Http\\Requests\\StoreNoteRequest;
use App\\Http\\Resources\\NoteResource;
use Illuminate\\Http\\JsonResponse;
use App\\Modules\\Notes\\CreateNote;
use App\\Modules\\Notes\\Note;
class NoteController extends Controller
{
    public function store(StoreNoteRequest $request, CreateNote $action): JsonResponse
    { return (new NoteResource($action->execute($request->validated('title'))))->response()->setStatusCode(201); }
    public function show(Note $note): NoteResource { return new NoteResource($note); }
}
''',
'routes/api/notes.php': '''<?php
use App\\Http\\Controllers\\Api\\NoteController;
use Illuminate\\Support\\Facades\\Route;
Route::post('/notes', [NoteController::class, 'store']);
Route::get('/notes/{note}', [NoteController::class, 'show']);
''',
 'tests/Feature/Notes/ApiTest.php': '''<?php
it('creates and reads a note', function () {
    $response = $this->postJson('/api/notes', ['title' => 'Hello'])->assertCreated()
        ->assertJsonPath('data.title', 'Hello')->assertJsonStructure(['data' => ['id', 'title']]);
    $id = $response->json('data.id');
    expect($id)->toBeInt();
    $this->assertDatabaseHas('notes', ['id' => $id, 'title' => 'Hello']);
    $this->getJson('/api/notes/'.$id)->assertOk()->assertJsonPath('data.title', 'Hello');
});
it('rejects an empty title', function () {
    $this->postJson('/api/notes', [])->assertUnprocessable()->assertJsonValidationErrors('title');
    $this->assertDatabaseCount('notes', 0);
});
it('rejects a title exceeding the limit', function () {
    $this->postJson('/api/notes', ['title' => str_repeat('x', 121)])->assertUnprocessable();
    $this->assertDatabaseCount('notes', 0);
});
it('returns 404 for an unknown note', function () {
    $this->getJson('/api/notes/999999')->assertNotFound();
});
'''}


def command(*args):
    print('$ ' + ' '.join(args), flush=True)
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        print(result.stdout)
        raise RuntimeError(f'command failed ({result.returncode}): {args}')
    return result.stdout


def cli(*args):
    result = command(sys.executable, '-m', 'srashta', *args)
    print(result, end='')
    return result


def write_files(files):
    for name, body in files.items():
        path = Path(name); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body)


def exercise(root):
    previous = os.getcwd()
    os.chdir(root)
    try:
        command('git','config','user.name','Srashta acceptance fixture')
        command('git','config','user.email','fixture@example.invalid')
        command('git','branch','-M','main')
        cfg=yaml.safe_load(Path('project.yaml').read_text())
        cfg['spec']['path']='spec/notes.md'
        cfg['modules']={'notes':['NOTE']}
        cfg['phases']={0:{'name':'Notes API','layer':'api','domains':['NOTE'],'gate':'Notes acceptance tests pass'}}
        cfg['verification_commands']=[['php','artisan','test','--compact','tests/Feature/Notes']]
        cfg['journeys']={'J1':{'name':'Capture a note','steps':[{'id':'J1.1','text':'Create a note'},{'id':'J1.2','text':'Read it later'}]}}
        cfg['shared_resources']={'api_routes':{'paths':['routes/api.php'],'strategy':'contract_only'}}
        Path('project.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
        write_files({'spec/notes.md':PRD, 'contracts/phase-0.md':CONTRACT,
          'tests/Pest.php': "<?php\npest()->extend(Tests\\TestCase::class)->use(Illuminate\\Foundation\\Testing\\RefreshDatabase::class)->in('Feature/Notes');\n",
          'constitution.md': 'Laravel 12, SQLite acceptance fixture, Pest tests. Controllers delegate writes to actions. No remote calls. No screens in this API phase.\n'})
        def ticket(id, files, reqs, deps=()):
            return dict(id=id,title='Define Notes contracts' if id.startswith('C') else 'Implement Notes API',
                module='notes',layer='api',depends_on=list(deps),owned_files=list(files),requirements=reqs,
                acceptance_tests=['Persist note schema'] if id.startswith('C') else ['201 and persistence for valid title','422 and no persistence for invalid title','200 for existing note','404 for missing note'],
                evidence=['Pest test output'],blocked_on=[],serves=['J1.1','J1.2'])
        reqs=['FR-NOTE-001','FR-NOTE-002']
        c=ticket('C-01',CONTRACT_FILES,reqs); c['contract_context']=CONTRACT;c['touches']=['api_routes']
        write_json('tickets/phase-0.json',[c,ticket('T-01',FEATURE_FILES,reqs,['C-01'])])
        cli('extract');cli('assign');cli('approve','0','--by','EXAMPLE FIXTURE — not a human approval')
        cli('waves','0');cli('validate','0');cli('packs','0');cli('export','0')
        command('git','add','.');command('git','commit','-qm','Approve example plan and scaffold')
        for tid, files in [('C-01',CONTRACT_FILES),('T-01',FEATURE_FILES)]:
            base=command('git','rev-parse','HEAD').strip()
            cli('event',tid,'attempt_started','--phase','0','--agent','scripted-acceptance-fixture')
            # Fixtures are deterministic implementations; the real orchestrator supplies its worker here.
            write_files(files)
            command('git','add',*files);command('git','commit','-qm',f'{tid}: implement example')
            cli('verify','0',tid,'--base',base)
            cli('event',tid,'brief_feedback','--phase','0','--data',json.dumps({'sufficient':True,'note':'Scripted fixture; not a model quality assessment.'}))
            head=command('git','rev-parse','HEAD').strip()
            cli('event',tid,'merged','--phase','0','--data',json.dumps({'head':head,'reviewed_by':'EXAMPLE FIXTURE'}))
            command('git','add','events','evidence');command('git','commit','-qm','Record example execution evidence')
        write_files({'retrospectives/phase-0.md':'# Example retrospective\nBoth API requirements verified. Fixture approvals and scripted implementation do not evaluate autonomous agent quality.\n'})
        cli('close','0','--by','EXAMPLE FIXTURE')
        print(command('php','artisan','migrate','--force'))
        cli('api','freeze','--by','EXAMPLE FIXTURE')
        command('git','add','retrospectives','docs');command('git','commit','-qm','Freeze example API')
        cli('api','check','--base','HEAD')
        contract=yaml.safe_load(Path('docs/openapi.yaml').read_text())
        assert '/notes' in contract['paths'] and '/notes/{note}' in contract['paths'], contract['paths'].keys()
        assert contract['components']['schemas']['NoteResource']['properties']['id']['type'] == 'integer'
        assert '201' in contract['paths']['/notes']['post']['responses']
        assert '422' in contract['paths']['/notes']['post']['responses']
        assert '404' in contract['paths']['/notes/{note}']['get']['responses']
        Path('DEMO.md').write_text('''# Verified Notes API fixture
Run `composer install`, copy `.env.example` to `.env`, then `php artisan key:generate`.
Run `php artisan test --compact tests/Feature/Notes` and `srashta api check --base HEAD`.
The Git history, phase source, generated briefs, execution evidence, closure and API freeze
record a complete local workflow. Approvals are fixture data. No hosted CI was run and no
external orchestrator or autonomous worker was used. This is an acceptance fixture, not a
production Notes application. The two endpoints are intentionally unauthenticated.
''')
        command('git','add','DEMO.md');command('git','commit','-qm','Document fixture limits')
        print('PASS: idea/spec -> approved plan -> verified commits -> closed phase -> frozen API')
    finally:
        os.chdir(previous)


if __name__=='__main__':
    destination=Path(sys.argv[1]).resolve()
    importlib.import_module('srashta.init').run('notes-demo',str(destination),'laravel-react',True)
    exercise(destination)
