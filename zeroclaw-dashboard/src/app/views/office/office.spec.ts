import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Office } from './office';

describe('Office', () => {
  let component: Office;
  let fixture: ComponentFixture<Office>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Office]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Office);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
