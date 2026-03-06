import { ComponentFixture, TestBed } from '@angular/core/testing';

import { People } from './people';

describe('People', () => {
  let component: People;
  let fixture: ComponentFixture<People>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [People]
    })
    .compileComponents();

    fixture = TestBed.createComponent(People);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
