# LazyLibrarian UX Modernization

## Requirements Document & Design Specifications

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | January 28, 2026 |
| **Status** | Draft for Review |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Design System](#design-system)
4. [Information Architecture](#information-architecture)
5. [Screen Specifications](#screen-specifications)
6. [Functional Requirements](#functional-requirements)
7. [Non-Functional Requirements](#non-functional-requirements)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Appendix](#appendix)

---

## Executive Summary

This document outlines the comprehensive UX modernization strategy for LazyLibrarian, a media automation application for managing eBooks, audiobooks, magazines, and author tracking. The current interface, while functional, reflects design patterns from an earlier era and presents opportunities for significant improvement in usability, visual appeal, and user satisfaction.

The modernization initiative will transform LazyLibrarian from a utilitarian, data-table-centric application into a visually engaging, intuitive media management experience. Drawing inspiration from modern portfolio management tools like LINQ Compass, we will implement a clean sidebar navigation, card-based dashboards, and a cohesive design system.

### Key Objectives

- **Modernize Visual Design:** Transition from dark, dated aesthetics to a light, clean interface with a teal accent color palette
- **Improve Navigation:** Replace horizontal tab navigation with persistent sidebar navigation
- **Add Dashboard View:** Provide at-a-glance library statistics and recent activity
- **Enhance Media Browsing:** Implement grid/card views for visual media discovery
- **Streamline Settings:** Consolidate and reorganize configuration options

---

## Current State Analysis

### Current Application Overview

LazyLibrarian is a self-hosted media automation application that helps users manage their digital library. The application currently supports eBooks, audiobooks, magazines, and author tracking with automated downloading capabilities.

### Core Features

- **Authors:** Track favorite authors and automatically search for new releases
- **eBooks:** Manage digital book library with metadata, ratings, and status tracking
- **Series:** Track book series completion and missing volumes
- **AudioBooks:** Similar management for audio format books
- **Magazines:** Subscribe to and manage magazine publications
- **Wanted List:** Queue of media actively being searched for
- **History/Logs:** Track download history and system activity

### Identified UX Issues

| Category | Issue | Impact |
|----------|-------|--------|
| **Visual Design** | Dark brown/maroon color scheme with low contrast | Eye strain, dated appearance, reduced accessibility |
| **Navigation** | Horizontal tabs with 8+ top-level items | Cognitive overload, hidden features, unclear hierarchy |
| **Data Display** | Dense tables as primary view for all content | Poor visual browsing, reduced discoverability |
| **Action Bars** | Multiple rows of toggle buttons and actions | Visual clutter, unclear primary actions |
| **Settings** | 8 sub-tabs with dense, unsorted options | Difficult configuration, missed features |
| **Overview** | No dashboard or summary view | Users must navigate to each section to see status |

---

## Design System

### Color Palette

The new color palette is inspired by modern SaaS applications, featuring a professional teal accent with clean neutrals for optimal readability.

| Color | Hex | Usage |
|-------|-----|-------|
| **Primary** | `#0D9488` | Main actions, active states, branding |
| **Primary Dark** | `#0F766E` | Hover states, emphasis |
| **Secondary** | `#64748B` | Secondary text, icons |
| **Accent** | `#F59E0B` | Ratings, highlights, warnings |
| **Success** | `#10B981` | Downloaded status, positive actions |
| **Warning** | `#F59E0B` | Wanted status, alerts |
| **Error** | `#EF4444` | Failed status, destructive actions |
| **Background** | `#F8FAFC` | Page background |
| **Surface** | `#FFFFFF` | Cards, panels |
| **Text** | `#1E293B` | Primary text |
| **Text Light** | `#64748B` | Secondary text, captions |
| **Border** | `#E2E8F0` | Dividers, input borders |

### Typography

- **Primary Font:** Inter (headings and body text)
- **Monospace Font:** JetBrains Mono (logs, code, technical data)
- **Base Size:** 14px for body text, 16px minimum touch targets
- **Scale:** 1.25 ratio (12, 14, 18, 22, 28, 36px)

### Component Library

The design system includes the following reusable components:

- **Buttons:** Primary, Secondary, Ghost, Danger variants with consistent padding
- **Cards:** Elevated containers with subtle shadows and hover states
- **Tables:** Clean data tables with sortable headers, pagination, and filters
- **Forms:** Consistent input fields, dropdowns, checkboxes, and toggles
- **Badges:** Status indicators (Downloaded, Wanted, Skipped, etc.)
- **Modals:** Dialogs for confirmations and detailed views
- **Toast Notifications:** Non-blocking feedback for actions

---

## Information Architecture

### Navigation Structure

The new navigation replaces the horizontal tab bar with a persistent left sidebar, grouping related functions and providing clear visual hierarchy.

| Section | Items | Description |
|---------|-------|-------------|
| **MAIN** | Dashboard | Overview with stats, recent activity, quick actions |
| **LIBRARY** | Authors, Books, Series, AudioBooks, Magazines | Core media management sections with grid and table views |
| **ACTIVITY** | Wanted, Downloads, History | Track search queue, active downloads, completed actions |
| **SYSTEM** | Logs, Settings | System monitoring and configuration |

---

## Screen Specifications

### 1. Dashboard

**Purpose:** Provide at-a-glance overview of library status and recent activity

#### Layout Components

1. **Statistics Cards Row:** Four cards showing: Total Authors, Total Books, AudioBooks, Magazines
2. **Library Composition:** Donut chart showing media type distribution
3. **Recent Activity:** Timeline of recent downloads, additions, and status changes
4. **Wanted Queue Summary:** Count of items being searched with quick link
5. **Quick Actions:** Add Author, Search Books, Library Scan buttons

---

### 2. Authors

**Purpose:** Browse and manage tracked authors

#### View Modes

- **Grid View (Default):** Card-based display with author photo, name, book count, status badge
- **Table View:** Dense list with sortable columns for power users

#### Toolbar Actions

- Search/filter by name
- Filter by status (Active, Paused, Ignored)
- Sort options (Name, Book Count, Last Updated)
- Add Author button (primary action)
- Bulk actions for selected items

---

### 3. Books (eBooks & AudioBooks)

**Purpose:** Browse, search, and manage book library

#### View Modes

- **Cover Grid (Default):** Visual browsing with book covers, title, author, rating stars
- **List View:** Compact rows with cover thumbnail, full metadata

#### Filters Panel

- Status: Downloaded, Wanted, Skipped, Ignored
- Format: eBook, AudioBook, Both
- Author (typeahead search)
- Series (typeahead search)
- Rating range slider
- Date range picker

---

### 4. Series

**Purpose:** Track series completion and discover missing volumes

#### Layout

- Expandable series rows showing completion percentage
- Progress bar visualization
- Expand to reveal individual book status (owned, wanted, missing)
- Quick action to want all missing books

---

### 5. Magazines

**Purpose:** Subscribe to and manage magazine collections

#### Layout

- Magazine cards with cover, title, issue count
- Status badge (Active subscription, Paused)
- Click to expand showing issue grid
- Add magazine via search

---

### 6. Wanted

**Purpose:** Monitor and manage the download queue

#### Layout

- Tabbed view: All, Books, AudioBooks, Magazines
- Progress indicators for active searches
- Status column: Searching, Found, Downloading, Failed
- Actions: Retry, Remove, Mark as Skipped
- Bulk retry/remove options

---

### 7. Downloads

**Purpose:** Monitor active and recent downloads

#### Layout

- Active downloads with progress bars
- Download speed and ETA
- Pause/Resume/Cancel actions
- Recently completed section

---

### 8. History

**Purpose:** View historical activity and completed actions

#### Layout

- Chronological list of all actions
- Filter by action type (Downloaded, Added, Removed, Failed)
- Date range picker
- Search within history
- Export functionality

---

### 9. Logs

**Purpose:** System monitoring and debugging

#### Layout

- Real-time log viewer with auto-scroll
- Log level filters (Debug, Info, Warning, Error)
- Search/filter logs
- Download log file
- Clear logs action

---

### 10. Settings

**Purpose:** Centralized configuration with logical grouping

#### Reorganized Settings Structure

| Section | Contents |
|---------|----------|
| **General** | Server settings, language, date formats, update checks |
| **Media Sources** | Google Books API, Goodreads integration, metadata providers |
| **Download Clients** | SABnzbd, NZBGet, Transmission, qBittorrent, Deluge configurations |
| **Indexers** | Newznab, Torznab, RSS providers with test functionality |
| **Processing** | Post-processing rules, file naming, folder structure |
| **Notifications** | Email, Slack, Telegram, Pushover, custom webhooks |
| **Import/Export** | Library import, CSV export, wishlist sync, backup/restore |

---

## Functional Requirements

### Navigation Requirements

| ID | Requirement |
|----|-------------|
| REQ-1 | Sidebar navigation SHALL be persistent and visible on all screens |
| REQ-2 | Sidebar SHALL be collapsible to icon-only mode on user action |
| REQ-3 | Active navigation item SHALL be visually highlighted |
| REQ-4 | Navigation sections SHALL be labeled with group headers |
| REQ-5 | Each navigation item SHALL display an icon and label |

### Dashboard Requirements

| ID | Requirement |
|----|-------------|
| REQ-6 | Dashboard SHALL display total counts for Authors, Books, AudioBooks, and Magazines |
| REQ-7 | Dashboard SHALL include a library composition visualization |
| REQ-8 | Dashboard SHALL show recent activity feed with last 10 actions |
| REQ-9 | Dashboard SHALL display wanted queue summary with counts by status |
| REQ-10 | Dashboard SHALL provide quick action buttons for common tasks |

### Library View Requirements

| ID | Requirement |
|----|-------------|
| REQ-11 | All library views SHALL support both grid and table display modes |
| REQ-12 | View mode preference SHALL persist across sessions |
| REQ-13 | Grid view SHALL display cover images with hover states showing actions |
| REQ-14 | Table view SHALL support column sorting by clicking headers |
| REQ-15 | All views SHALL support filtering by status, author, series, and date range |
| REQ-16 | Search SHALL filter results in real-time as user types |
| REQ-17 | Pagination SHALL support configurable page sizes (24, 48, 96, All) |

### Media Item Requirements

| ID | Requirement |
|----|-------------|
| REQ-18 | Each item SHALL display status using colored badges |
| REQ-19 | Rating SHALL be displayed using star visualization (1-5) |
| REQ-20 | Clicking an item SHALL open detail view/modal |
| REQ-21 | Bulk selection SHALL be supported with checkbox selection |
| REQ-22 | Context menu SHALL provide quick actions (Want, Skip, Ignore, Delete) |

### Settings Requirements

| ID | Requirement |
|----|-------------|
| REQ-23 | Settings SHALL be organized into logical groups with sub-navigation |
| REQ-24 | Each setting SHALL include help text explaining its purpose |
| REQ-25 | Provider configurations SHALL include test connectivity button |
| REQ-26 | Changes SHALL require explicit save action |
| REQ-27 | Unsaved changes SHALL prompt warning before navigation |

---

## Non-Functional Requirements

### Performance

- Initial page load SHALL complete within 2 seconds
- Navigation between views SHALL complete within 500ms
- Search results SHALL begin appearing within 300ms of typing
- Grid views SHALL implement virtual scrolling for large datasets (>100 items)

### Accessibility

- Interface SHALL meet WCAG 2.1 AA standards
- All interactive elements SHALL be keyboard navigable
- Color contrast SHALL meet minimum 4.5:1 ratio for text
- All images SHALL have appropriate alt text
- Focus states SHALL be clearly visible

### Responsive Design

- **Desktop (1200px+):** Full sidebar, multi-column grid
- **Tablet (768-1199px):** Collapsible sidebar, reduced grid columns
- **Mobile (< 768px):** Bottom navigation bar, single column, touch-optimized

### Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

- Implement new design system (colors, typography, components)
- Build sidebar navigation framework
- Create reusable component library (cards, tables, buttons, forms)
- Set up responsive breakpoints and grid system

### Phase 2: Core Views (Weeks 4-6)

- Implement Dashboard with statistics and activity feed
- Build Books view with grid/list toggle
- Build Authors view with grid/list toggle
- Implement filtering and search functionality

### Phase 3: Secondary Views (Weeks 7-9)

- Build Series tracking view
- Build AudioBooks view
- Build Magazines view
- Implement Wanted queue and History views

### Phase 4: Settings & Polish (Weeks 10-12)

- Redesign Settings with new organization
- Implement toast notifications
- Add keyboard shortcuts
- Performance optimization and testing
- Accessibility audit and fixes

---

## Appendix

### Status Badge Specifications

| Status | Color | Hex | Usage |
|--------|-------|-----|-------|
| **Downloaded** | Green | `#10B981` | Item is in the library and available |
| **Wanted** | Amber | `#F59E0B` | Actively searching for this item |
| **Skipped** | Gray | `#64748B` | User chose not to download (temporary) |
| **Ignored** | Gray | `#94A3B8` | Permanently excluded from searches |
| **Failed** | Red | `#EF4444` | Download attempted but failed |
| **Active** | Teal | `#0D9488` | Author/Magazine actively monitored |
| **Paused** | Amber | `#F59E0B` | Monitoring temporarily suspended |

### Icon Reference

All icons should use the Lucide icon set for consistency. Key icons:

- Dashboard: `LayoutGrid`
- Authors: `User`
- Books: `Book`
- Series: `ClipboardList`
- AudioBooks: `Headphones`
- Magazines: `FileText`
- Wanted: `Clock`
- Downloads: `Download`
- History: `History`
- Logs: `FileText`
- Settings: `Settings`

---

*— End of Document —*
