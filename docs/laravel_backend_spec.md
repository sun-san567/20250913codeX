# Laravel バックエンド設計（体重/運動トラッカー）

この文書は、現在の Streamlit アプリのバックエンドを Laravel に置き換えるための設計です。最小構成で REST API を提供し、将来的にフロントエンド（Streamlit/React/Vue 等）から呼び出せるようにします。

## 目的と方針

- データ保存を CSV から DB（SQLite/MySQL/PostgreSQL）へ移行
- バリデーションと集計ロジックをサーバー側で一元化
- 既存要件の踏襲（体重は小数1位、運動は整数分、期間プリセット、統計、CSV入出力 など）

## エンティティとテーブル設計

1. weights（体重）
   - date: DATE PK（1日1件）
   - weight: DECIMAL(5,1) 20.0–300.0
   - timestamps

2. exercises（運動）
   - id: BIGINT PK
   - date: DATE（日毎集計のため）
   - activity: VARCHAR(120)
   - duration_min: INT（0–1440）
   - UNIQUE(date, activity)
   - timestamps

3. settings（設定）
   - id: BIGINT PK
   - key: VARCHAR(64)（例: goal_weight）
   - value: JSON（例: {"goal_weight": 62.0}）
   - timestamps

推奨インデックス:
- exercises(date), exercises(activity)

## 期間プリセット

- 1週間=7d, 1ヶ月=30d, 3ヶ月=90d, 半年=180d, 1年=365d, 全期間=all

## エンドポイント定義（例）

Base URL: `/api`

### 体重（weights）

- GET `/weights?range=7d|30d|90d|180d|365d|all`
  - 応答: [{ date: 'YYYY-MM-DD', weight: 63.1 }]
- GET `/weights/stats?window=7|30`
  - 応答: { avg: 63.1, delta: 0.5, min: 62.6, max: 63.8 }
- POST `/weights`
  - 入力: { date: 'YYYY-MM-DD', weight: 63.1 }
  - バリデーション: weight 20.0–300.0、小数1位
  - 既存があれば上書き
- DELETE `/weights/{date}`
  - 指定日のレコードを削除
- GET `/weights/export.csv`
  - 全件を CSV 出力（ヘッダ: date,weight）
- POST `/weights/import` (任意)
  - CSV アップロードでマージ（同日重複はアップロード側優先）

### 運動（exercises）

- GET `/exercises?range=7d|...|all`
  - 応答: [{ id, date, activity, duration_min }]
- GET `/exercises/daily?range=7d|...|all`
  - 日毎合計: [{ date, total_min }]
- GET `/exercises/by-activity?range=7d|...|all`
  - 種目別日毎: [{ date, activity, duration_min }]
- POST `/exercises`
  - 入力: { date, activity, duration_min }
  - バリデーション: duration_min 0–1440（整数）、(date, activity) で upsert
- DELETE `/exercises/{id}` or `/exercises/by-key?date=YYYY-MM-DD&activity=胸`
- GET `/exercises/export.csv`
- POST `/exercises/import` (任意)

### 設定（settings）

- GET `/settings/goal-weight`
  - 応答: { goal_weight: 62.0|null }
- POST `/settings/goal-weight`
  - 入力: { goal_weight: 62.0 }（小数1位、20.0–300.0）

## Laravel 実装手順（Laravel 10+）

1. プロジェクト作成
   ```bash
   composer create-project laravel/laravel weight-tracker-api
   cd weight-tracker-api
   php artisan key:generate
   ```

2. モデル/マイグレーション/コントローラ生成
   ```bash
   php artisan make:model Weight -mcr
   php artisan make:model Exercise -mcr
   php artisan make:model Setting -mcr
   php artisan make:request StoreWeightRequest
   php artisan make:request StoreExerciseRequest
   ```

3. マイグレーション例
   ```php
   // database/migrations/xxxx_create_weights_table.php
   Schema::create('weights', function (Blueprint $table) {
       $table->date('date')->primary();
       $table->decimal('weight', 5, 1);
       $table->timestamps();
   });

   // database/migrations/xxxx_create_exercises_table.php
   Schema::create('exercises', function (Blueprint $table) {
       $table->id();
       $table->date('date');
       $table->string('activity', 120);
       $table->unsignedInteger('duration_min');
       $table->timestamps();
       $table->unique(['date', 'activity']);
       $table->index('date');
   });

   // database/migrations/xxxx_create_settings_table.php
   Schema::create('settings', function (Blueprint $table) {
       $table->id();
       $table->string('key', 64)->unique();
       $table->json('value')->nullable();
       $table->timestamps();
   });
   ```

4. バリデーション（FormRequest）
   ```php
   // app/Http/Requests/StoreWeightRequest.php
   public function rules() {
       return [
           'date' => ['required','date'],
           'weight' => ['required','numeric','between:20,300'],
       ];
   }
   protected function prepareForValidation(){
       if ($this->weight !== null) {
           $this->merge(['weight' => round((float)$this->weight, 1)]);
       }
   }

   // app/Http/Requests/StoreExerciseRequest.php
   public function rules() {
       return [
           'date' => ['required','date'],
           'activity' => ['required','string','max:120'],
           'duration_min' => ['required','integer','between:0,1440'],
       ];
   }
   ```

5. コントローラ（抜粋）
   ```php
   // app/Http/Controllers/WeightController.php
   class WeightController extends Controller {
       public function index(Request $req) {
           $range = $req->query('range','7d');
           $q = Weight::query()->orderBy('date');
           if ($range !== 'all') {
               $days = match($range) {
                   '7d' => 7, '30d' => 30, '90d' => 90, '180d' => 180, '365d' => 365,
                   default => 30,
               };
               $q->where('date', '>=', now()->subDays($days-1)->toDateString());
           }
           return response()->json($q->get());
       }
       public function store(StoreWeightRequest $req) {
           $data = $req->validated();
           Weight::updateOrCreate(['date'=>$data['date']], ['weight'=>$data['weight']]);
           return response()->noContent();
       }
       public function destroy(string $date) {
           Weight::where('date',$date)->delete();
           return response()->noContent();
       }
       public function stats(Request $req) {
           $win = (int)$req->query('window', 7);
           $from = now()->subDays($win-1)->toDateString();
           $rows = Weight::where('date','>=',$from)->orderBy('date')->get();
           if ($rows->isEmpty()) return response()->json(['avg'=>null,'delta'=>null,'min'=>null,'max'=>null]);
           $avg = round($rows->avg('weight'), 1);
           $delta = round($rows->last()->weight - $rows->first()->weight, 1);
           return response()->json([
               'avg'=>$avg,
               'delta'=>$delta,
               'min'=>round($rows->min('weight'),1),
               'max'=>round($rows->max('weight'),1),
           ]);
       }
   }
   ```

   ```php
   // app/Http/Controllers/ExerciseController.php（抜粋）
   class ExerciseController extends Controller {
       public function index(Request $req) { /* range で絞り込み */ }
       public function store(StoreExerciseRequest $req) {
           $d = $req->validated();
           Exercise::updateOrCreate(
               ['date'=>$d['date'], 'activity'=>$d['activity']],
               ['duration_min'=>$d['duration_min']]
           );
           return response()->noContent();
       }
       public function destroyByKey(Request $req) {
           Exercise::where('date',$req->query('date'))
               ->where('activity',$req->query('activity'))
               ->delete();
           return response()->noContent();
       }
       public function daily(Request $req) { /* groupBy(date) の合計 */ }
       public function byActivity(Request $req) { /* date×activity の合計 */ }
   }
   ```

6. ルーティング（routes/api.php）
   ```php
   Route::get('/weights', [WeightController::class,'index']);
   Route::get('/weights/stats', [WeightController::class,'stats']);
   Route::post('/weights', [WeightController::class,'store']);
   Route::delete('/weights/{date}', [WeightController::class,'destroy']);
   Route::get('/weights/export.csv', [WeightExportController::class,'export']);

   Route::get('/exercises', [ExerciseController::class,'index']);
   Route::get('/exercises/daily', [ExerciseController::class,'daily']);
   Route::get('/exercises/by-activity', [ExerciseController::class,'byActivity']);
   Route::post('/exercises', [ExerciseController::class,'store']);
   Route::delete('/exercises/by-key', [ExerciseController::class,'destroyByKey']);

   Route::get('/settings/goal-weight', [SettingController::class,'getGoal']);
   Route::post('/settings/goal-weight', [SettingController::class,'setGoal']);
   ```

7. CORS / 認証

- 開発中は CORS を許可（`app/Http/Middleware/HandleCors.php` または `config/cors.php`）
- 将来的に認証（Laravel Sanctum）を導入してトークン保護

8. CSV エクスポート/インポート（任意）

- Export: `League\Csv` などでストリーム出力
- Import: アップロード→行ごとにバリデーション→Upsert（アップロード優先）

## Streamlit からの移行/連携

選択肢 A: 既存の Streamlit をフロントとして維持し、API 呼び出しに置換
- Python 側は `requests` で上記エンドポイントをコール
- ローカル検証は SQLite + `php artisan serve` で OK

選択肢 B: Web フロント（React/Vue）へ移行
- Vite + Vue/React で UI を再構築、API は同一

## Docker（任意）

`docker-compose.yml` 例（Nginx + PHP-FPM + MySQL）

```yaml
services:
  app:
    build: .
    volumes: [".:/var/www/html"]
    environment:
      - APP_ENV=local
  web:
    image: nginx:alpine
    volumes: ["./nginx.conf:/etc/nginx/conf.d/default.conf", ".:/var/www/html"]
    ports: ["8080:80"]
    depends_on: [app]
  db:
    image: mysql:8
    environment:
      MYSQL_DATABASE: tracker
      MYSQL_ROOT_PASSWORD: root
    ports: ["3306:3306"]
```

---

この設計で進めてよければ、初期プロジェクトの雛形（モデル/マイグレーション/コントローラ/ルート）を生成するスクリプトと、Streamlit 側の API 呼び出し差し替えパッチを用意します。必要な DB（SQLite/MySQL）と認証有無をご指定ください。

