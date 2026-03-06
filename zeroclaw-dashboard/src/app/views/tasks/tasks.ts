import { Component, OnInit, HostListener, signal, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DragDropModule, CdkDragDrop, moveItemInArray, transferArrayItem } from '@angular/cdk/drag-drop';
import { Zeroclaw } from '../../services/zeroclaw';

@Component({
  selector: 'app-tasks',
  imports: [CommonModule, FormsModule, DragDropModule],
  templateUrl: './tasks.html',
  styleUrl: './tasks.css'
})
export class Tasks implements OnInit {
  public tasks = {
    recurring: [] as any[],
    backlog: [] as any[],
    inProgress: [] as any[],
    review: [] as any[]
  };

  public showQuickAdd = false;
  public newTaskTitle = '';

  public rawTasks = signal<any[]>([]);

  constructor(private zeroclaw: Zeroclaw, private cdr: ChangeDetectorRef) { }

  async ngOnInit() {
    await this.loadTasks();
  }

  async loadTasks() {
    try {
      const data = await this.zeroclaw.getTasks();
      this.rawTasks.set(data || []);
      this.distributeTasks();
      this.cdr.detectChanges();
      console.log('Tasks loaded:', this.rawTasks().length);
    } catch (err) {
      console.error('Failed to load tasks', err);
    }
  }

  distributeTasks() {
    const all = this.rawTasks();
    this.tasks = {
      recurring: all.filter(t => t.status === 'recurring'),
      backlog: all.filter(t => t.status === 'backlog'),
      inProgress: all.filter(t => t.status === 'inProgress'),
      review: all.filter(t => t.status === 'review')
    };
  }

  /** Press N anywhere on the page to focus quick add */
  @HostListener('document:keydown', ['$event'])
  onKeydown(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement).tagName;
    if (e.key === 'n' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
      e.preventDefault();
      this.showQuickAdd = true;
      setTimeout(() => {
        const input = document.getElementById('quick-add-input');
        if (input) input.focus();
      }, 50);
    }
    if (e.key === 'Escape' && this.showQuickAdd) {
      this.cancelQuickAdd();
    }
  }

  get totalCount() { return this.rawTasks().length; }
  get inProgressCount() { return this.tasks.inProgress.length; }
  get backlogCount() { return this.tasks.backlog.length; }
  get reviewCount() { return this.tasks.review.length; }

  async drop(event: CdkDragDrop<any[]>, targetStatus: string) {
    if (event.previousContainer === event.container) {
      moveItemInArray(event.container.data, event.previousIndex, event.currentIndex);
    } else {
      transferArrayItem(
        event.previousContainer.data,
        event.container.data,
        event.previousIndex,
        event.currentIndex,
      );
      // Update the status of the moved item
      const movedItem = event.container.data[event.currentIndex];
      movedItem.status = targetStatus;
    }

    // Rebuild rawTasks from distributed state to ensure perfect sync
    const flatTasks = [
      ...this.tasks.recurring,
      ...this.tasks.backlog,
      ...this.tasks.inProgress,
      ...this.tasks.review
    ];

    this.rawTasks.set(flatTasks);

    // Explicitly sync to backend
    await this.zeroclaw.updateTasks(this.rawTasks());
  }

  toggleQuickAdd() {
    this.showQuickAdd = !this.showQuickAdd;
    if (this.showQuickAdd) {
      this.newTaskTitle = '';
      setTimeout(() => document.getElementById('quick-add-input')?.focus(), 50);
    }
  }

  cancelQuickAdd() {
    this.showQuickAdd = false;
    this.newTaskTitle = '';
  }

  async submitNewTask() {
    if (!this.newTaskTitle.trim()) {
      this.cancelQuickAdd();
      return;
    }

    const newTask = {
      id: `TSK-${Date.now().toString().slice(-4)}${Math.floor(Math.random() * 100)}`,
      title: this.newTaskTitle.trim(),
      status: "backlog",
      agent: "Unassigned",
      project: "General",
      date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    };

    this.rawTasks.update(current => [...current, newTask]);
    await this.zeroclaw.updateTasks(this.rawTasks());
    this.distributeTasks();
    this.cancelQuickAdd();
  }

  async editTask(task: any) {
    const newTitle = window.prompt("Edit task title:", task.title);
    if (!newTitle || newTitle === task.title) return;

    task.title = newTitle.trim();
    await this.zeroclaw.updateTasks(this.rawTasks());
    this.distributeTasks();
  }

  async deleteTask(id: string) {
    if (!window.confirm("Are you sure you want to delete this task?")) return;

    this.rawTasks.update(current => current.filter(t => t.id !== id));
    await this.zeroclaw.updateTasks(this.rawTasks());
    this.distributeTasks();
  }
}
