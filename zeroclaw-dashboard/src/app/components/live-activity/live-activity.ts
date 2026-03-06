import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Zeroclaw } from '../../services/zeroclaw';

@Component({
  selector: 'app-live-activity',
  imports: [CommonModule],
  templateUrl: './live-activity.html',
  styleUrl: './live-activity.css'
})
export class LiveActivity {
  public zeroClaw = inject(Zeroclaw);
}
