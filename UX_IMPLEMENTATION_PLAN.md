# LazyLibrarian UX Modernization - Implementation Plan

## Document Purpose

This plan provides detailed, actionable guidance for modernizing the LazyLibrarian UI from the current Bootstrap 5 dark theme to the new teal/light sidebar-based design. It is designed to span multiple implementation sessions and context windows.

---

## Current State Summary

### Existing Technology Stack
- **Template Engine:** Mako (inheritance via `base.html`)
- **CSS Framework:** Bootstrap 5 with Bootswatch dark themes
- **JavaScript:** jQuery 1.12, DataTables, Bootbox modals
- **Icons:** FontAwesome 5
- **Layout:** Horizontal top navigation bar with dropdown menus

### Key Files (Current)
| File | Purpose | Lines |
|------|---------|-------|
| `data/interfaces/bookstrap/base.html` | Master template with nav | ~400 |
| `data/css/bookstrap.css` | Custom Bootstrap overrides | ~775 |
| `data/interfaces/bookstrap/index.html` | Authors list page | ~266 |
| `data/interfaces/bookstrap/books.html` | Books list page | ~280 |
| `data/interfaces/bookstrap/config.html` | Settings page | ~3000+ |

### Current UI Issues (from Requirements)
1. Dark brown/maroon color scheme with low contrast
2. Horizontal tabs with 8+ top-level items
3. Dense tables as primary view for all content
4. Multiple rows of toggle buttons and actions
5. Settings with 8 sub-tabs and dense, unsorted options
6. No dashboard or summary view

---

## Target State Summary

### New Design System
- **Color Palette:** Teal primary (#0D9488), light background (#F8FAFC)
- **Typography:** Inter font family, 14px base
- **Icons:** Lucide (SVG-based, inline)
- **Layout:** Fixed left sidebar (240px), main content area

### New Navigation Structure
```
MAIN
  └── Dashboard

LIBRARY
  ├── Authors
  ├── Books
  ├── Series
  ├── AudioBooks
  └── Magazines

ACTIVITY
  ├── Wanted
  ├── Downloads
  └── History

SYSTEM
  ├── Logs
  └── Settings
```

### Key New Features
1. Dashboard with statistics cards and activity feed
2. Grid/List view toggle for all library pages
3. Visual card-based browsing
4. Reorganized settings with logical grouping
5. Toast notifications

---

## Implementation Strategy

### Approach: Parallel Theme Development

Rather than modifying the existing `bookstrap` theme in-place (which risks breaking the working UI), we will:

1. **Create a new theme directory:** `data/interfaces/modern/`
2. **Create a new CSS file:** `data/css/modern.css`
3. **Add a theme selector:** Allow users to switch between `bookstrap` and `modern`
4. **Incremental migration:** Port pages one at a time, keeping both working

### Benefits
- Zero risk to existing functionality
- Users can switch back if issues arise
- Enables side-by-side comparison during development
- Can be tested thoroughly before becoming default

---

## Phase 1: Foundation (Estimated: 3-4 sessions)

### 1.1 Create Theme Infrastructure

**Files to Create:**
```
data/interfaces/modern/
├── base.html              # New master template with sidebar
├── index.html             # Dashboard (new page)
└── placeholder.html       # Fallback for unmigrated pages

data/css/
└── modern.css             # Complete new design system CSS
```

**Tasks:**
- [ ] Create `data/interfaces/modern/` directory
- [ ] Create `modern.css` with complete design system:
  - CSS custom properties (color palette)
  - Sidebar styles
  - Card components
  - Button variants
  - Form controls
  - Status badges
  - Table styles
  - Grid/list view styles
- [ ] Create `base.html` with:
  - Sidebar navigation structure
  - Main content area
  - JavaScript for navigation highlighting
  - Font loading (Inter from CDN)
- [ ] Create Dashboard page (index.html) with:
  - Statistics cards
  - Activity feed (populated from API)
  - Quick actions
  - Library composition chart
- [ ] Add `HTTP_LOOK` config option for `modern` theme
- [ ] Test theme switching

**Key Implementation Details:**

The sidebar navigation in `base.html` needs to:
1. Render all navigation items based on user permissions (using existing `perm` checks)
2. Highlight the active page
3. Support collapsible mode for mobile

### 1.2 Design System CSS (`modern.css`)

**CSS Structure:**
```css
/* 1. CSS Custom Properties */
:root {
    --primary: #0D9488;
    --primary-dark: #0F766E;
    --primary-light: #CCFBF1;
    /* ... all colors from design system */
}

/* 2. Reset and Base Styles */
/* 3. Typography */
/* 4. Sidebar Navigation */
/* 5. Main Content Layout */
/* 6. Cards and Panels */
/* 7. Buttons */
/* 8. Forms */
/* 9. Tables */
/* 10. Status Badges */
/* 11. Grid/List Views */
/* 12. Pagination */
/* 13. Activity Feed */
/* 14. Progress Bars */
/* 15. Modals/Dialogs */
/* 16. Toast Notifications */
/* 17. Responsive Breakpoints */
```

### 1.3 Backend Changes

**Files to Modify:**
- `lazylibrarian/__init__.py` - Add `modern` to allowed HTTP_LOOK values
- `lazylibrarian/webServe.py` - Add dashboard API endpoint
- `lazylibrarian/api.py` - Add getStats command for dashboard data

**New API Endpoints Needed:**
```python
# Get dashboard statistics
def getStats():
    return {
        'authors': count_authors(),
        'books': count_books(),
        'audiobooks': count_audiobooks(),
        'magazines': count_magazines(),
        'wanted': count_wanted(),
        'recent_activity': get_recent_activity(limit=10)
    }
```

---

## Phase 2: Core Library Views (Estimated: 4-5 sessions)

### 2.1 Authors Page

**File:** `data/interfaces/modern/authors.html`

**Features:**
- Grid view (default): Author cards with photo, name, book count, status
- List view: DataTables-based table
- View toggle (grid/list) with cookie persistence
- Filter by status (Active/Paused/Ignored)
- Search filter
- "Add Author" button
- Bulk selection and actions

**Implementation Notes:**
- Reuse existing DataTables server-side processing (`getIndex` endpoint)
- Grid view needs client-side data or new endpoint
- Card click opens author detail page

### 2.2 Books Page

**File:** `data/interfaces/modern/books.html`

**Features:**
- Grid view (default): Book cover cards with title, author, rating, status
- List view: DataTables-based table
- View toggle with persistence
- Filter by status, author, series, format
- Search filter
- Pagination controls

**Implementation Notes:**
- Existing `books.html` uses DataTables with server-side processing
- Need cover image display in grid view
- Consider lazy loading for large libraries

### 2.3 Series Page

**File:** `data/interfaces/modern/series.html`

**Features:**
- Expandable series rows
- Progress bar visualization
- "Want Missing" quick action
- Filter by completion status

### 2.4 AudioBooks Page

**File:** `data/interfaces/modern/audio.html`

**Features:**
- Similar to Books page
- Different color scheme for audiobook cards
- Duration display
- Narrator information

### 2.5 Magazines Page

**File:** `data/interfaces/modern/magazines.html`

**Features:**
- Magazine cards with cover, title, issue count
- Status badge (Active/Paused)
- Click to expand issues
- "Add Magazine" button

---

## Phase 3: Activity Views (Estimated: 2-3 sessions)

### 3.1 Wanted Page

**File:** `data/interfaces/modern/manage.html`

**Features:**
- Tabbed view: All, Books, AudioBooks, Magazines
- Status indicators (Searching, Found, Downloading, Failed)
- Actions: Retry, Remove, Skip
- Bulk actions

### 3.2 Downloads Page

**File:** `data/interfaces/modern/downloads.html`

**Features:**
- Active downloads with progress bars
- Download speed and ETA
- Pause/Resume/Cancel actions
- Recently completed section

**New Backend Requirement:**
- May need websocket or polling for real-time progress

### 3.3 History Page

**File:** `data/interfaces/modern/history.html`

**Features:**
- Chronological activity list
- Filter by action type
- Date range picker
- Search within history
- Export functionality

---

## Phase 4: Settings & Polish (Estimated: 3-4 sessions)

### 4.1 Settings Redesign

**File:** `data/interfaces/modern/config.html`

**New Organization:**
| Section | Contents |
|---------|----------|
| General | Server, language, date formats, updates |
| Media Sources | Google Books, Goodreads APIs |
| Download Clients | SABnzbd, NZBGet, Transmission, etc. |
| Indexers | Newznab, Torznab, RSS providers |
| Processing | Post-processing rules, file naming |
| Notifications | Email, Slack, Telegram, etc. |
| Import/Export | CSV, backup, restore |

**Features:**
- Sub-navigation on left
- Test connectivity buttons
- Help text for each setting
- Save confirmation
- Unsaved changes warning

### 4.2 Logs Page

**File:** `data/interfaces/modern/logs.html`

**Features:**
- Real-time log viewer with auto-scroll
- Log level filters (Debug, Info, Warning, Error)
- Search/filter logs
- Download log file
- Clear logs action

### 4.3 Toast Notifications

**Implementation:**
- Replace bootbox alerts with toast notifications
- Non-blocking feedback for actions
- Success/warning/error variants
- Auto-dismiss with configurable duration

### 4.4 Keyboard Shortcuts

**Common Shortcuts:**
- `/` - Focus search
- `g d` - Go to Dashboard
- `g a` - Go to Authors
- `g b` - Go to Books
- `n` - New (context-dependent)

### 4.5 Accessibility Audit

**Checklist:**
- [ ] All interactive elements keyboard navigable
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 minimum)
- [ ] Focus states clearly visible
- [ ] Alt text for images
- [ ] ARIA labels where needed

---

## File Change Summary

### New Files to Create

```
data/interfaces/modern/
├── base.html                 # Master template with sidebar
├── index.html                # Dashboard
├── authors.html              # Authors (grid/list)
├── author.html               # Author detail page
├── books.html                # Books (grid/list)
├── audio.html                # AudioBooks (grid/list)
├── series.html               # Series tracking
├── members.html              # Series members
├── magazines.html            # Magazines
├── issues.html               # Magazine issues
├── manage.html               # Wanted queue
├── downloads.html            # Active downloads
├── history.html              # Download history
├── logs.html                 # System logs
├── config.html               # Settings
├── login.html                # Login page
├── register.html             # Registration
├── profile.html              # User profile
├── search.html               # Search results
├── manualsearch.html         # Manual search
├── editbook.html             # Book editor
├── editauthor.html           # Author editor
├── choosetype.html           # Media type selector
├── response.html             # API response page
├── shutdown.html             # Shutdown confirmation
├── dbupdate.html             # Database update
├── dlresult.html             # Download result
├── users.html                # User management
├── opds.html                 # OPDS info
├── coverwall.html            # Cover wall view
└── managebooks.html          # Manage books (alternate)

data/css/
└── modern.css                # New design system CSS (~1500 lines)

data/js/
└── modern.js                 # New theme JavaScript (~500 lines)
```

### Files to Modify

```
lazylibrarian/__init__.py     # Add HTTP_LOOK 'modern' option
lazylibrarian/webServe.py     # Add dashboard route, stats API
lazylibrarian/webStart.py     # Register modern template directory
lazylibrarian/api.py          # Add getStats command
```

---

## Testing Strategy

### Unit Tests
- Test new API endpoints (getStats)
- Test theme switching logic

### Manual Testing Checklist
For each page in the new theme:
- [ ] Page loads without errors
- [ ] All buttons/links functional
- [ ] Data displays correctly
- [ ] Filters work
- [ ] Search works
- [ ] Pagination works
- [ ] Mobile responsive
- [ ] Keyboard navigation
- [ ] Permissions enforced

### Browser Testing
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Session Tracking

Use this section to track progress across implementation sessions.

### Session 1: January 28, 2026
**Completed:**
- Created `data/interfaces/modern/` directory
- Created `data/css/modern.css` - Complete design system CSS (~1200 lines)
  - CSS custom properties for all colors, typography, spacing
  - Sidebar navigation styles
  - Card, button, form, table, badge components
  - Grid/list view styles
  - Activity feed, progress bars, pagination
  - Responsive breakpoints
  - Toast notifications, modals
- Created `data/interfaces/modern/base.html` - Master template with sidebar navigation
  - Full sidebar with permission-based navigation items
  - Mobile responsive header
  - Toast notification system
  - View toggle functionality with cookie persistence
- Created `data/interfaces/modern/index.html` - Dashboard page
  - Statistics cards (Authors, Books, AudioBooks, Magazines)
  - Quick action buttons
  - Recent activity feed
  - Library composition donut chart
  - Wanted queue summary
  - System status alerts
- Created `data/interfaces/modern/login.html` - Login page with modern styling
- Created `data/interfaces/modern/authors.html` - Authors page with grid/list toggle
  - Grid view with author cards
  - List view with DataTables integration
  - Search and filter functionality
  - Bulk selection and actions
- Created `data/interfaces/modern/response.html` - API response page
- Modified `lazylibrarian/webServe.py`:
  - Updated `home()` method to serve dashboard for modern theme
  - Added `_serve_dashboard()` helper with statistics queries
  - Updated `serve_template()` to pass username to templates

**Files Created:**
- `data/interfaces/modern/base.html`
- `data/interfaces/modern/index.html`
- `data/interfaces/modern/login.html`
- `data/interfaces/modern/authors.html`
- `data/interfaces/modern/response.html`
- `data/css/modern.css`

**Files Modified:**
- `lazylibrarian/webServe.py` (added dashboard support)

**Tests:** All 542 tests passing

**Next Session:**
- Create remaining library pages (books.html, series.html, audio.html, magazines.html)
- Create activity pages (manage.html, history.html, logs.html)
- Port config.html with reorganized settings
- Add more pages: profile.html, register.html, author.html detail page

---

### Session 2: January 28, 2026
**Completed:**
- Created `data/interfaces/modern/books.html` - Books page with grid/list toggle
  - DataTables integration for list view
  - Grid view with book cover cards
  - Status badges (Open, Wanted, Snatched, etc.)
  - Bulk selection and actions
- Created `data/interfaces/modern/series.html` - Series page with progress bars
  - Visual progress bars showing completion percentage
  - Status filtering (All, Complete, Partial, Empty, etc.)
  - Links to series members
- Created `data/interfaces/modern/audio.html` - AudioBooks page
  - Similar structure to books.html
  - Headphones icon badge for audiobook identification
  - Grid view with audiobook cards
- Created `data/interfaces/modern/magazines.html` - Magazines page
  - Add magazine form at top
  - Grid/list view toggle
  - Issue count badges
- Created `data/interfaces/modern/author.html` - Author detail page
  - Author header card with image, stats, and progress bar
  - Author action buttons (Refresh, Pause, Remove, etc.)
  - Books list with DataTables
  - Language and library filters
- Created `data/interfaces/modern/members.html` - Series members page
  - Series book list in reading order
  - Both eBook and AudioBook status display
  - Bulk selection and actions
- Created `data/interfaces/modern/issues.html` - Magazine issues page
  - Grid/list view toggle
  - Issue covers and dates
  - Open/download actions
- Modified `lazylibrarian/webServe.py`:
  - Added `/authors` route for modern theme authors list

**Files Created:**
- `data/interfaces/modern/books.html`
- `data/interfaces/modern/series.html`
- `data/interfaces/modern/audio.html`
- `data/interfaces/modern/magazines.html`
- `data/interfaces/modern/author.html`
- `data/interfaces/modern/members.html`
- `data/interfaces/modern/issues.html`

**Files Modified:**
- `lazylibrarian/webServe.py` (added /authors route)

**Tests:** All 542 tests passing

**Next Session (Phase 3 & 4):**
- Create manage.html (Wanted queue)
- Create history.html (Download history)
- Create logs.html (System logs)
- Create config.html (Settings with reorganized sections)
- Create profile.html, register.html, users.html
- Create remaining utility pages (editbook.html, editauthor.html, etc.)

---

## Quick Reference

### Color Palette
| Name | Hex | Usage |
|------|-----|-------|
| Primary | #0D9488 | Actions, active states |
| Primary Dark | #0F766E | Hover states |
| Primary Light | #CCFBF1 | Backgrounds |
| Success | #10B981 | Downloaded status |
| Warning | #F59E0B | Wanted status |
| Error | #EF4444 | Failed status |
| Background | #F8FAFC | Page background |
| Surface | #FFFFFF | Cards, panels |
| Text | #1E293B | Primary text |
| Text Light | #64748B | Secondary text |
| Border | #E2E8F0 | Dividers |

### Status Badges
| Status | Color | Class |
|--------|-------|-------|
| Downloaded | Green | `.status-downloaded` |
| Wanted | Amber | `.status-wanted` |
| Skipped | Gray | `.status-skipped` |
| Ignored | Gray | `.status-ignored` |
| Failed | Red | `.status-failed` |
| Active | Teal | `.status-active` |
| Paused | Amber | `.status-paused` |
| Searching | Blue | `.status-searching` |
| Downloading | Teal | `.status-downloading` |

### Navigation Items
| Section | Icon | Route |
|---------|------|-------|
| Dashboard | LayoutGrid | /home |
| Authors | User | /home (index) |
| Books | Book | /books |
| Series | ClipboardList | /series |
| AudioBooks | Headphones | /audio |
| Magazines | FileText | /magazines |
| Wanted | Clock | /manage |
| Downloads | Download | /downloads (new) |
| History | History | /history |
| Logs | FileText | /logs |
| Settings | Settings | /config |

---

## Implementation Order

**Recommended sequence for optimal progress:**

1. **modern.css** - Complete CSS first (foundation for everything)
2. **base.html** - Master template with sidebar
3. **index.html** - Dashboard (new feature, high impact)
4. **authors.html** - Port authors page (exercises grid/list toggle)
5. **books.html** - Port books page (similar to authors)
6. **series.html** - Series tracking
7. **audio.html** - AudioBooks (similar to books)
8. **magazines.html** - Magazines
9. **manage.html** - Wanted queue
10. **history.html** - History
11. **logs.html** - Logs
12. **config.html** - Settings (most complex, save for last)
13. Remaining utility pages

---

## Success Criteria

The modernization is complete when:

1. All pages render correctly in the new theme
2. All existing functionality works identically
3. Dashboard provides meaningful at-a-glance information
4. Grid/list views work with preference persistence
5. Settings are reorganized and easier to navigate
6. WCAG 2.1 AA accessibility standards are met
7. Performance is equal to or better than current theme
8. Users can switch between themes without issues
