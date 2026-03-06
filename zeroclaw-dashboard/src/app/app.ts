import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Zeroclaw } from './services/zeroclaw';
import { CommonModule } from '@angular/common';
import { Sidebar } from './components/sidebar/sidebar';
import { Topbar } from './components/topbar/topbar';
import { LiveActivity } from './components/live-activity/live-activity';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, CommonModule, Sidebar, Topbar, LiveActivity],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  public zeroClaw = inject(Zeroclaw);
}
