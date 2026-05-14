# Frontend Components and Architecture

Complete guide to the ExecOS frontend SPA, component architecture, styling, and development patterns.

## Table of Contents

1. [Frontend Overview](#frontend-overview)
2. [Technology Stack](#technology-stack)
3. [Page Structure](#page-structure)
4. [Component Patterns](#component-patterns)
5. [State Management](#state-management)
6. [API Integration](#api-integration)
7. [Styling and Tailwind](#styling-and-tailwind)
8. [Adding New Pages](#adding-new-pages)
9. [Performance Optimization](#performance-optimization)

---

## Frontend Overview

### Architecture

ExecOS frontend is a **Single Page Application (SPA)** built with:

- **HTML/CSS/JavaScript** - Zero-build approach
- **Alpine.js** - Interactive components (from CDN)
- **Tailwind CSS** - Utility-first styling (from CDN)
- **Fetch API** - HTTP requests to backend
- **Local Storage** - Client-side state persistence

**Key Principle:** No build step, no NPM, no webpack. Pure HTML with Alpine.js for interactivity.

### File Structure

```
web/static/
├── index.html          # Single HTML file containing:
│                       #   - 27 pages (divs with x-show)
│                       #   - Alpine.js components
│                       #   - Inline CSS
│                       #   - Tailwind CDN
│                       #   - All JavaScript
└── (no other files)
```

The entire frontend is **one HTML file** (~500KB). This is intentional:
- Fast load time
- No asset pipeline needed
- Easy to modify
- Version controlled with git

---

## Technology Stack

### Frontend Libraries (from CDN)

```html
<!-- Alpine.js - Reactive UI -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

<!-- Tailwind CSS - Styling -->
<link href="https://cdn.tailwindcss.com" rel="stylesheet">
```

### Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ JavaScript support required
- LocalStorage API required

### No Build Dependencies

- No npm/yarn needed
- No webpack/bundler
- No transpilation
- Deploy the HTML file directly

---

## Page Structure

### 27 Pages Overview

All 27 pages are in a single HTML file, toggled via Alpine.js:

```html
<div x-show="currentPage === 'dashboard'" id="page-dashboard">
  <!-- Dashboard page content -->
</div>

<div x-show="currentPage === 'tasks'" id="page-tasks">
  <!-- Tasks page content -->
</div>

<!-- ... 25 more pages ... -->
```

### Core Pages (Primary UX)

| Page | ID | Purpose | Key Features |
|------|----|---------|----|
| Dashboard | `dashboard` | Overview, quick stats | Overdue, in-progress, upcoming |
| Tasks | `tasks` | Task management | CRUD, filtering, bulk actions |
| Projects | `projects` | Project overview | Health score, progress bars |
| Milestones | `milestones` | Milestone tracking | Timeline view, overdue highlight |
| Commitments | `commitments` | Promise tracking | Pending/fulfilled/missed |
| Alerts | `alerts` | Notifications | Severity levels, read/snooze |
| Releases | `releases` | Version management | UAT, sign-off dates |
| Team Members | `team` | Team management | Capacity, allocation |
| Applications | `applications` | Product tracking | Integration settings |

### Summary Pages

| Page | Purpose |
|------|---------|
| SOD (Start of Day) | Overdue, due today, carry-forward |
| EOD (End of Day) | Completed, still pending |
| Operational Dashboard | Live metrics |
| Executive Dashboard | Portfolio health |

### Integration Pages

| Page | Purpose |
|------|---------|
| Jira Settings | Jira integration config |
| GitLab Settings | GitLab integration config |
| Email Settings | SOD/EOD email setup |
| Outlook Settings | Calendar integration |
| Estimations | Work effort estimation |
| Daily Plan | Time-blocked schedule |

### Admin Pages

| Page | Purpose |
|------|---------|
| Settings | Global configuration |
| Activity Logs | API audit trail |
| Admin Console | System management |

---

## Component Patterns

### Alpine.js Component Pattern

#### Basic Component Structure

```html
<div x-data="taskComponent()" @task-created.window="refreshTasks()">
  <!-- Display data -->
  <template x-for="task in tasks">
    <div x-text="task.title"></div>
  </template>

  <!-- Forms -->
  <form @submit.prevent="createTask()">
    <input x-model="newTask.title" placeholder="Task title">
    <button type="submit">Create</button>
  </form>
</div>

<script>
function taskComponent() {
  return {
    tasks: [],
    newTask: { title: '', priority: 'medium' },

    init() {
      this.loadTasks();
    },

    async loadTasks() {
      const response = await fetch('/api/tasks');
      this.tasks = await response.json();
    },

    async createTask() {
      const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.newTask)
      });

      if (response.ok) {
        this.tasks.push(await response.json());
        this.newTask = { title: '', priority: 'medium' };
        // Trigger event for other components
        window.dispatchEvent(new CustomEvent('task-created'));
      }
    }
  }
}
</script>
```

#### Component Lifecycle

```javascript
{
  // 1. Initialize data
  items: [],
  loading: false,
  error: null,

  // 2. Alpine calls init() on mount
  init() {
    this.loadData();
  },

  // 3. Load data from API
  async loadData() {
    this.loading = true;
    try {
      const resp = await fetch('/api/items');
      this.items = await resp.json();
    } catch (e) {
      this.error = e.message;
    } finally {
      this.loading = false;
    }
  },

  // 4. Handle user interactions
  async deleteItem(id) {
    await fetch(`/api/items/${id}`, { method: 'DELETE' });
    this.items = this.items.filter(i => i.id !== id);
  }
}
```

### Common UI Patterns

#### Modal Dialog

```html
<div x-data="{ open: false }">
  <button @click="open = true">Open Modal</button>

  <div x-show="open" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
    <div class="bg-white rounded-lg p-6">
      <h2 class="text-xl font-bold">Dialog Title</h2>
      <p>Dialog content here</p>
      <button @click="open = false">Close</button>
    </div>
  </div>
</div>
```

#### Dropdown Menu

```html
<div x-data="{ open: false }" class="relative">
  <button @click="open = !open" class="px-4 py-2 bg-blue-500 text-white rounded">
    Menu
  </button>

  <div x-show="open" @click.away="open = false" class="absolute bg-white border rounded shadow">
    <a href="#" class="block px-4 py-2 hover:bg-gray-100">Option 1</a>
    <a href="#" class="block px-4 py-2 hover:bg-gray-100">Option 2</a>
  </div>
</div>
```

#### Tab Navigation

```html
<div x-data="{ activeTab: 'tab1' }">
  <div class="flex border-b">
    <button 
      @click="activeTab = 'tab1'" 
      :class="{ 'border-b-2 border-blue-500': activeTab === 'tab1' }"
      class="px-4 py-2">
      Tab 1
    </button>
    <button 
      @click="activeTab = 'tab2'"
      :class="{ 'border-b-2 border-blue-500': activeTab === 'tab2' }"
      class="px-4 py-2">
      Tab 2
    </button>
  </div>

  <div x-show="activeTab === 'tab1'" class="p-4">Content 1</div>
  <div x-show="activeTab === 'tab2'" class="p-4">Content 2</div>
</div>
```

#### Form with Validation

```html
<form @submit.prevent="handleSubmit()" x-data="formData()">
  <div class="mb-4">
    <label class="block text-sm font-bold mb-2">Title</label>
    <input 
      x-model="form.title" 
      type="text" 
      required
      class="w-full border rounded px-3 py-2"
    >
    <span x-show="errors.title" class="text-red-500 text-sm" x-text="errors.title"></span>
  </div>

  <div class="mb-4">
    <label class="block text-sm font-bold mb-2">Priority</label>
    <select x-model="form.priority" class="w-full border rounded px-3 py-2">
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
    </select>
  </div>

  <button type="submit" :disabled="isSubmitting" class="bg-blue-500 text-white px-4 py-2 rounded">
    <span x-show="!isSubmitting">Submit</span>
    <span x-show="isSubmitting">Loading...</span>
  </button>
</form>

<script>
function formData() {
  return {
    form: { title: '', priority: 'medium' },
    errors: {},
    isSubmitting: false,

    async handleSubmit() {
      this.errors = {};
      this.isSubmitting = true;

      // Validate
      if (!this.form.title) {
        this.errors.title = 'Title is required';
      }

      if (Object.keys(this.errors).length > 0) {
        this.isSubmitting = false;
        return;
      }

      // Submit
      try {
        const response = await fetch('/api/items', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form)
        });

        if (response.ok) {
          // Success handling
          this.form = { title: '', priority: 'medium' };
        } else {
          this.errors.submit = 'Failed to submit';
        }
      } finally {
        this.isSubmitting = false;
      }
    }
  }
}
</script>
```

---

## State Management

### Local Storage Persistence

```javascript
// Save to localStorage
function saveState(key, data) {
  localStorage.setItem(`execos_${key}`, JSON.stringify(data));
}

// Load from localStorage
function loadState(key, defaultValue) {
  const data = localStorage.getItem(`execos_${key}`);
  return data ? JSON.parse(data) : defaultValue;
}

// Usage in component
{
  filters: loadState('task_filters', { status: 'todo' }),

  init() {
    this.loadTasks();
  },

  updateFilters(newFilters) {
    this.filters = newFilters;
    saveState('task_filters', this.filters);
    this.loadTasks();
  }
}
```

### Cross-Component Communication

#### Window Events

```javascript
// Component A - Dispatch event
function deleteTask(taskId) {
  fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
  window.dispatchEvent(new CustomEvent('task-deleted', {
    detail: { taskId }
  }));
}

// Component B - Listen for event
{
  init() {
    window.addEventListener('task-deleted', (e) => {
      this.tasks = this.tasks.filter(t => t.id !== e.detail.taskId);
    });
  }
}
```

---

## API Integration

### Fetch Wrapper Helper

```javascript
// Reusable API client
const api = {
  async get(endpoint) {
    const response = await fetch(`/api${endpoint}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  async post(endpoint, data) {
    const response = await fetch(`/api${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  async patch(endpoint, data) {
    const response = await fetch(`/api${endpoint}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  async delete(endpoint) {
    const response = await fetch(`/api${endpoint}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.ok;
  }
}

// Usage
{
  async loadTasks() {
    try {
      this.tasks = await api.get('/tasks?status=todo');
    } catch (e) {
      this.error = e.message;
    }
  }
}
```

### Error Handling

```javascript
{
  async loadData() {
    try {
      this.data = await api.get('/endpoint');
      this.error = null;
    } catch (e) {
      this.error = `Failed to load: ${e.message}`;
      console.error(e);
    }
  }
}
```

---

## Styling and Tailwind

### Tailwind CSS Classes

ExecOS uses Tailwind CSS from CDN. No custom CSS needed in most cases.

#### Common Classes

```html
<!-- Colors -->
<div class="bg-blue-500 text-white">Blue background</div>
<div class="text-red-600">Red text</div>
<div class="border border-gray-300">Gray border</div>

<!-- Spacing -->
<div class="p-4">Padding 1rem</div>
<div class="m-2">Margin 0.5rem</div>
<div class="mb-4">Margin bottom</div>

<!-- Layout -->
<div class="flex items-center justify-between">Flexbox</div>
<div class="grid grid-cols-3 gap-4">3-column grid</div>

<!-- Responsive -->
<div class="text-sm md:text-base lg:text-lg">Responsive text</div>
<div class="block md:flex">Block on mobile, flex on desktop</div>

<!-- Hover/Active States -->
<button class="bg-blue-500 hover:bg-blue-600 active:bg-blue-700">Button</button>

<!-- Transitions -->
<div class="transition duration-200 ease-in-out">Smooth transition</div>
```

#### Custom Styles (if needed)

Add inline `<style>` tag in `<head>`:

```html
<style>
  .custom-class {
    /* Custom CSS here */
  }
</style>
```

### Theme Colors

- **Primary:** Blue (Tailwind's `blue-500` to `blue-700`)
- **Secondary:** Gray (Tailwind's `gray-*`)
- **Success:** Green (`green-500`)
- **Warning:** Amber (`amber-500`)
- **Danger:** Red (`red-500`)
- **Info:** Cyan (`cyan-500`)

---

## Adding New Pages

### Step-by-Step Guide

#### 1. Add Page Content to HTML

```html
<div x-show="currentPage === 'newpage'" id="page-newpage" class="p-6">
  <h1 class="text-3xl font-bold mb-6">New Page Title</h1>

  <!-- Page content here -->
  <div x-data="newPageComponent()">
    <!-- Component markup -->
  </div>
</div>
```

#### 2. Add Navigation Link

Find the navigation/sidebar and add:

```html
<button 
  @click="currentPage = 'newpage'"
  :class="{ 'bg-blue-100': currentPage === 'newpage' }"
  class="w-full text-left px-4 py-2 hover:bg-gray-100">
  New Page
</button>
```

#### 3. Implement Component

Add component JavaScript function (before the closing `</body>` tag):

```javascript
function newPageComponent() {
  return {
    items: [],
    loading: false,

    init() {
      this.loadData();
    },

    async loadData() {
      this.loading = true;
      try {
        this.items = await api.get('/endpoint');
      } finally {
        this.loading = false;
      }
    }
  }
}
```

#### 4. Test

1. Save the HTML file
2. Refresh browser
3. Click navigation link to new page
4. Verify functionality

### Example: Complete New Page

```html
<!-- In body, add page div -->
<div x-show="currentPage === 'custompage'" id="page-custompage" class="p-6">
  <h1 class="text-3xl font-bold mb-6">Custom Items</h1>

  <div x-data="customPageComponent()" x-init="init()">
    <!-- Loading state -->
    <div x-show="loading" class="text-center py-8">
      <p class="text-gray-600">Loading...</p>
    </div>

    <!-- Content -->
    <div x-show="!loading">
      <!-- Add new item form -->
      <form @submit.prevent="addItem()" class="mb-6 p-4 bg-gray-50 rounded">
        <input 
          x-model="newItem.title" 
          placeholder="Item title"
          class="w-full border rounded px-3 py-2 mb-2"
        >
        <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded">
          Add Item
        </button>
      </form>

      <!-- Items list -->
      <div class="space-y-2">
        <template x-for="item in items" :key="item.id">
          <div class="p-4 border rounded flex justify-between">
            <span x-text="item.title"></span>
            <button 
              @click="deleteItem(item.id)"
              class="text-red-500 hover:text-red-700">
              Delete
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</div>

<!-- In script section, add component function -->
<script>
function customPageComponent() {
  return {
    items: [],
    newItem: { title: '' },
    loading: false,

    async init() {
      await this.loadItems();
    },

    async loadItems() {
      this.loading = true;
      try {
        this.items = await api.get('/api/custom-items');
      } finally {
        this.loading = false;
      }
    },

    async addItem() {
      if (!this.newItem.title) return;
      
      const created = await api.post('/api/custom-items', this.newItem);
      this.items.push(created);
      this.newItem = { title: '' };
    },

    async deleteItem(id) {
      await api.delete(`/api/custom-items/${id}`);
      this.items = this.items.filter(i => i.id !== id);
    }
  }
}
</script>
```

---

## Performance Optimization

### Load Time Optimization

1. **Lazy Load Heavy Components:**
```javascript
// Defer loading until visible
async loadOnDemand() {
  const response = await fetch('/api/heavy-data');
  this.data = await response.json();
}
```

2. **Debounce Search Input:**
```javascript
{
  search: '',
  searchTimeout: null,

  async onSearchInput() {
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.performSearch();
    }, 300); // Wait 300ms after user stops typing
  }
}
```

3. **Batch API Requests:**
```javascript
// Instead of fetching each task separately
async loadDashboard() {
  const [tasks, projects, alerts] = await Promise.all([
    api.get('/tasks?status=todo'),
    api.get('/projects'),
    api.get('/alerts?unread_only=true')
  ]);
  this.tasks = tasks;
  this.projects = projects;
  this.alerts = alerts;
}
```

### Render Performance

1. **Limit x-for Repetitions:**
```html
<!-- Bad: 1000+ items in DOM -->
<template x-for="item in allItems">
  <div>...</div>
</template>

<!-- Good: Paginate or virtualize -->
<template x-for="item in paginatedItems">
  <div>...</div>
</template>
```

2. **Avoid Deep Nesting:**
```html
<!-- Bad: Too many Alpine scopes -->
<div x-data="...">
  <div x-data="...">
    <div x-data="...">
      <div x-if="..."></div>
    </div>
  </div>
</div>

<!-- Good: Flat structure -->
<div x-data="...">
  <div x-if="..."></div>
</div>
```

---

## Browser Developer Tools Tips

### Debug Alpine.js

```javascript
// In browser console
// Access component data
document.querySelectorAll('[x-data]')[0].__x.$data

// Trigger Alpine reactivity
document.querySelectorAll('[x-data]')[0].__x.currentPage = 'tasks'
```

### Inspect Network Requests

1. Open DevTools (F12)
2. Go to Network tab
3. Reload page
4. See all API calls
5. Click request to view headers and response

### Local Storage Debugging

```javascript
// View saved state
localStorage.getItem('execos_task_filters')

// Clear all ExecOS data
Object.keys(localStorage)
  .filter(k => k.startsWith('execos_'))
  .forEach(k => localStorage.removeItem(k))
```

---

## Common Issues and Solutions

### Page Not Showing

**Problem:** New page div not appearing

**Solution:**
1. Check `x-show="currentPage === 'pagename'"`
2. Verify button sets `currentPage = 'pagename'`
3. Check browser console for errors

### Data Not Loading

**Problem:** API call failing silently

**Solution:**
```javascript
async loadData() {
  try {
    this.data = await api.get('/endpoint');
  } catch (e) {
    console.error('Failed to load:', e);
    this.error = e.message;
  }
}
```

Check DevTools Network tab for 404 or 500 errors.

### Styles Not Applied

**Problem:** Tailwind classes not working

**Solution:**
1. Verify Tailwind CDN is loading
2. Check browser DevTools Elements tab for class names
3. Ensure classes are in HTML (not dynamically generated invalid)
4. Try inline style as fallback: `style="color: red;"`

