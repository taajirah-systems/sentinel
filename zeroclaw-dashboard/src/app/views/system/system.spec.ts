import { ComponentFixture, TestBed } from '@angular/core/testing';

import { System } from './system';

describe('System', () => {
  let component: System;
  let fixture: ComponentFixture<System>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [System]
    })
    .compileComponents();

    fixture = TestBed.createComponent(System);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
