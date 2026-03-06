import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Council } from './council';

describe('Council', () => {
  let component: Council;
  let fixture: ComponentFixture<Council>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Council]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Council);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
